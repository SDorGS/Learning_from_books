import re
import string
import idna
from urllib.parse import unquote


# ==========================
# Utility and Helper Methods
# ==========================

def percent_decode(s: str) -> str:
    """Decode percent-encoded characters safely."""
    try:
        return unquote(s)
    except Exception:
        return s  # Fallback for malformed encodings


def is_ascii_alpha(ch):
    return ch.isalpha() and ch in string.ascii_letters


def contains_non_ascii(s):
    return any(ord(c) > 127 for c in s)


def default_port(scheme):
    defaults = {
        "http": 80,
        "https": 443,
        "ftp": 21,
        "ws": 80,
        "wss": 443,
    }
    return defaults.get(scheme, None)


def split_once(s, delim):
    parts = s.split(delim, 1)
    return parts if len(parts) == 2 else (parts[0], "")


def split_last(s, delim):
    parts = s.rsplit(delim, 1)
    return parts if len(parts) == 2 else (parts[0], "")


def is_digit_string(s):
    return s.isdigit()


def parse_ipv6(buffer):
    # Very simplified IPv6 literal parser
    if buffer.startswith('[') and ']' in buffer:
        host = buffer[1:buffer.index(']')]
        port = ""
        remainder = buffer[buffer.index(']') + 1:]
        if remainder.startswith(':'):
            port = remainder[1:]
        return host, port
    return buffer, ""


# ===================
# URI Utilities Class
# ===================

class URIUtilities:
    @staticmethod
    def normalize_host(host):
        host = host.strip().strip('.').lower()
        if contains_non_ascii(host):
            host = idna.encode(host).decode('ascii')
        return host

    @staticmethod
    def normalize_port(port, scheme):
        if not port or not is_digit_string(port):
            return ""
        port_num = int(port)
        if default_port(scheme) == port_num:
            return ""
        return str(port_num)

    @staticmethod
    def normalize_path(path, scheme):
        if scheme in ["http", "https", "ftp", "file", "ws", "wss"] and not path.startswith('/'):
            path = '/' + path

        segments = []
        for seg in path.split('/'):
            if seg == '' or seg == '.':
                continue
            if seg == '..' and segments:
                segments.pop()
            elif seg != '..':
                segments.append(seg)
        return '/' + '/'.join(segments)

    @staticmethod
    def normalize(builder, handler):
        builder.scheme = builder.scheme.lower()
        if builder.host:
            builder.host = builder.host.lower()


# =========================
# URI Object and Builder
# =========================

class URIObject:
    def __init__(self, scheme, username, password, host, port, path, query, fragment, opaque):
        self.scheme = scheme
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.path = path
        self.query = query
        self.fragment = fragment
        self.opaque = opaque

    def __repr__(self):
        return f"<URIObject {self.to_string()}>"

    def to_string(self):
        if self.opaque:
            return f"{self.scheme}:{self.opaque}"

        uri = f"{self.scheme}://"
        if self.username:
            uri += self.username
            if self.password:
                uri += f":{self.password}"
            uri += "@"

        uri += self.host
        if self.port:
            uri += f":{self.port}"
        uri += self.path or "/"

        if self.query:
            uri += f"?{self.query}"
        if self.fragment:
            uri += f"#{self.fragment}"

        return uri


class URIBuilder:
    def __init__(self):
        self.scheme = ""
        self.username = ""
        self.password = ""
        self.host = ""
        self.port = ""
        self.path = ""
        self.query = ""
        self.fragment = ""
        self.opaque = ""

    def set_scheme(self, s): self.scheme = s
    def set_userinfo(self, u, p): self.username, self.password = u, p
    def set_host_port(self, h, p): self.host, self.port = h, p
    def set_path(self, p): self.path = p
    def set_query(self, q): self.query = q
    def set_fragment(self, f): self.fragment = f
    def set_opaque(self, o): self.opaque = o

    def build(self):
        return URIObject(
            scheme=self.scheme,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            path=self.path,
            query=self.query,
            fragment=self.fragment,
            opaque=self.opaque
        )


# =====================
# Abstract Base Handler
# =====================

class AbstractURIHandler:
    def parse(self, input_str, index, builder):
        raise NotImplementedError


# =====================
# Hierarchical Handler
# =====================

class HierarchicalHandler(AbstractURIHandler):
    def parse(self, input_str, index, builder):
        slash_count = 0
        RFC3986_MODE = True

        # Consume slashes or backslashes
        while index < len(input_str) and input_str[index] in ['/', '\\']:
            if input_str[index] == '\\':
                RFC3986_MODE = False
            slash_count += 1
            index += 1

        # Validate
        if slash_count < 2 and RFC3986_MODE:
            raise ValueError("Expected '//' after scheme")

        # Authority
        index = self._parse_authority(input_str, index, builder, RFC3986_MODE)

        # Path
        index = self._parse_path(input_str, index, builder)

        # Query
        index = self._parse_query(input_str, index, builder)

        # Fragment
        self._parse_fragment(input_str, index, builder)

    def _parse_authority(self, input_str, index, builder, RFC3986_MODE):
        buffer = ""
        username = password = host = port = ""
        in_userinfo = True

        while index < len(input_str) and input_str[index] not in ['/', '?', '#']:
            c = input_str[index]
            if c == '@':
                if ':' in buffer:
                    username, password = split_once(buffer, ':')
                else:
                    username = buffer
                builder.set_userinfo(percent_decode(username), percent_decode(password))
                buffer = ""
                in_userinfo = False
            else:
                buffer += c
            index += 1

        if '[' in buffer and ']' in buffer:
            host, port = parse_ipv6(buffer)
        elif ':' in buffer:
            host, port = split_last(buffer, ':')
        else:
            host, port = buffer, ""

        host = URIUtilities.normalize_host(host)
        port = URIUtilities.normalize_port(port, builder.scheme)
        builder.set_host_port(host, port)
        return index

    def _parse_path(self, input_str, index, builder):
        path = ""
        while index < len(input_str) and input_str[index] not in ['?', '#']:
            path += input_str[index]
            index += 1
        path = URIUtilities.normalize_path(path, builder.scheme)
        builder.set_path(path)
        return index

    def _parse_query(self, input_str, index, builder):
        if index < len(input_str) and input_str[index] == '?':
            index += 1
            query = ""
            while index < len(input_str) and input_str[index] != '#':
                query += input_str[index]
                index += 1
            builder.set_query(query)
        return index

    def _parse_fragment(self, input_str, index, builder):
        if index < len(input_str) and input_str[index] == '#':
            index += 1
            fragment = input_str[index:]
            builder.set_fragment(fragment)


# ==================
# Opaque URI Handler
# ==================

class OpaqueHandler(AbstractURIHandler):
    def parse(self, input_str, index, builder):
        opaque_part = input_str[index:]
        builder.set_opaque(opaque_part)


# ===================
# Handler Factory
# ===================

class URIHandlerFactory:
    @staticmethod
    def get_handler(scheme):
        scheme = scheme.lower()
        mapping = {
            "http": HierarchicalHandler(),
            "https": HierarchicalHandler(),
            "ftp": HierarchicalHandler(),
            "file": HierarchicalHandler(),
            "urn": OpaqueHandler(),
            "mailto": OpaqueHandler(),
            "tel": OpaqueHandler(),
            "news": OpaqueHandler(),
        }
        return mapping.get(scheme, HierarchicalHandler())


# ====================
# Main URI Parser
# ====================

class URIParser:
    def __init__(self):
        self.input = ""
        self.index = 0
        self.builder = URIBuilder()

    def parse(self, input_string):
        self.input = input_string.strip()
        self.index = 0
        self.builder = URIBuilder()

        # Scheme
        scheme = self._parse_scheme()
        self.builder.set_scheme(scheme)

        # Handler
        handler = URIHandlerFactory.get_handler(scheme)

        # Delegate parse
        handler.parse(self.input, self.index, self.builder)

        # Normalize
        URIUtilities.normalize(self.builder, handler)

        # Build final
        return self.builder.build()

    def _parse_scheme(self):
        start = self.index
        while self.index < len(self.input) and is_ascii_alpha(self.input[self.index]):
            self.index += 1

        if self.index == start or self.index >= len(self.input) or self.input[self.index] != ':':
            raise ValueError("Missing or invalid scheme")

        scheme = self.input[start:self.index].lower()
        self.index += 1
        return scheme


# ===================
# Example Usage
# ===================

if __name__ == "__main__":
    parser = URIParser()

    test_urls = [
        "https://user:pass@example.com:8080/path/to/file?query=value#fragment",
        "mailto:user@example.com",
        "urn:isbn:0451450523",
        "ftp://example.org/resource.txt",
        "file:///C:/Windows/System32",
        "news:comp.lang.python",
    ]

    for url in test_urls:
        uri = parser.parse(url)
        print(f"\nInput: {url}\nParsed: {uri}\nFields: {uri.__dict__}")

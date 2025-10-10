
## **1. Class Structure**

```text
URIParser                # Entry point / Template controller
│
├── URIHandlerFactory    # Returns handler based on scheme
│
├── AbstractURIHandler   # Base interface for all handlers
│   ├── HierarchicalHandler (e.g., HTTPHandler, FTPHandler)
│   └── OpaqueHandler        (e.g., URNHandler, MailtoHandler)
│
└── URIBuilder           # Collects parsed parts into final URI object
```

---

## **2. Core Algorithm (Template Method)**

```text
class URIParser:
    def parse(self, input_string):
        self.input = input_string.trim()
        self.index = 0
        self.builder = URIBuilder()

        # 1. Extract scheme
        scheme = self._parse_scheme()
        self.builder.set_scheme(scheme)

        # 2. Get scheme handler
        handler = URIHandlerFactory.get_handler(scheme)

        # 3. Delegate parsing to handler
        handler.parse(self.input, self.index, self.builder)

        # 4. Final normalization
        URIUtilities.normalize(self.builder, handler)

        # 5. Return finalized object
        return self.builder.build()
```

---

## **4. Scheme Parsing (Common to All)**

```text
function _parse_scheme():
    start = index
    while index < len(input) and is_ascii_alpha(input[index]):
        index += 1
    if index == start or index == len(input) or input[index] != ':':
        raise Error("Missing or invalid scheme")
    scheme = lowercase(input[start:index])
    index += 1   # skip ':'
    return scheme
```

---

## **5. Handler Factory**

```text
class URIHandlerFactory:
    mapping = {
        "http":  HTTPHandler(),
        "https": HTTPHandler(),
        "ftp":   HTTPHandler(),
        "file":  FileHandler(),
        "urn":   URNHandler(),
        "mailto":MailtoHandler(),
        "tel":   TelHandler(),
        "news":  NewsHandler(),
    }

    static function get_handler(scheme):
        if scheme in mapping:
            return mapping[scheme]
        else:
            return GenericHandler()   # Default hierarchical handler
```

---

## **6. Abstract Handler Interface**

```text
class AbstractURIHandler:
    def parse(input, index, builder):
        raise NotImplementedError
```

---

## **7. Hierarchical Handler Template**

### **(Used for HTTP, HTTPS, FTP, FILE, WS, WSS, etc.)**

```text
class HierarchicalHandler(AbstractURIHandler):
    def parse(input, index, builder):

        slash_count = 0
        RFC3986_MODE = True

        # Step 1: Consume slashes/backslashes
        while index < len(input) and input[index] in ['/', '\\']:
            if input[index] == '\\':
                RFC3986_MODE = False
            slash_count += 1
            index += 1

        # Step 2: Validate slash count
        if slash_count < 2 and RFC3986_MODE:
            raise Error("Expected '//' after scheme")
        if slash_count > 2:
            RFC3986_MODE = False  # extra slashes tolerated (WHATWG)

        # Step 3: Parse authority
        index = self._parse_authority(input, index, builder, RFC3986_MODE)

        # Step 4: Parse path
        index = self._parse_path(input, index, builder)

        # Step 5: Parse query
        index = self._parse_query(input, index, builder)

        # Step 6: Parse fragment
        self._parse_fragment(input, index, builder)
```

---

### **7a. Authority Parsing**

```text
function _parse_authority(input, index, builder, RFC3986_MODE):

    username, password, host, port = "", "", "", ""
    buffer = ""
    in_userinfo = True

    while index < len(input) and input[index] not in ['/', '?', '#']:
        c = input[index]

        if c == '@':
            # Split user:pass@
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

    # Now buffer holds host[:port]
    if '[' in buffer and ']' in buffer:
        # IPv6 literal
        host, port = parse_ipv6(buffer)
    elif ':' in buffer:
        host, port = split_last(buffer, ':')
    else:
        host, port = buffer, ""

    host = URIUtilities.normalize_host(host)
    port = URIUtilities.normalize_port(port, builder.scheme)
    builder.set_host_port(host, port)

    return index
```

---

### **7b. Path Parsing**

```text
function _parse_path(input, index, builder):
    path = ""
    while index < len(input) and input[index] not in ['?', '#']:
        path += input[index]
        index += 1
    path = URIUtilities.normalize_path(path, builder.scheme)
    builder.set_path(path)
    return index
```

---

### **7c. Query and Fragment Parsing**

```text
function _parse_query(input, index, builder):
    if index < len(input) and input[index] == '?':
        index += 1
        query = ""
        while index < len(input) and input[index] != '#':
            query += input[index]
            index += 1
        builder.set_query(query)
    return index

function _parse_fragment(input, index, builder):
    if index < len(input) and input[index] == '#':
        index += 1
        fragment = input[index:]
        builder.set_fragment(fragment)
```

---

## **8. Opaque Handler**

### **(Used for URNs, mailto, tel, news, etc.)**

```text
class OpaqueHandler(AbstractURIHandler):
    def parse(input, index, builder):
        opaque_part = input[index:]
        builder.set_opaque(opaque_part)
        # Opaque URIs have no authority/path/query/fragment
```

---

## **9. Utility Module**

```text
class URIUtilities:

    static function normalize_host(host):
        host = lowercase(host.strip('.'))
        if contains_non_ascii(host):
            host = idna_to_ascii(host)
        return host

    static function normalize_port(port, scheme):
        if not port:
            return ""
        if not is_digit_string(port):
            return ""
        port_num = int(port)
        if port_num == default_port(scheme):
            return ""
        return str(port_num)

    static function normalize_path(path, scheme):
        if scheme in special_schemes and not path.startswith('/'):
            path = '/' + path
        segments = []
        for segment in split(path, '/'):
            if segment == '' or segment == '.':
                continue
            if segment == '..' and segments:
                segments.pop()
            elif segment != '..':
                segments.append(segment)
        return '/' + join(segments, '/')

    static function normalize(builder, handler):
        builder.scheme = lowercase(builder.scheme)
        builder.host = lowercase(builder.host)
```

---

## **10. URI Builder Pattern**

```text
class URIBuilder:
    scheme = ""
    username = ""
    password = ""
    host = ""
    port = ""
    path = ""
    query = ""
    fragment = ""
    opaque = ""

    def set_scheme(self, s):       self.scheme = s
    def set_userinfo(self, u, p):  self.username, self.password = u, p
    def set_host_port(self, h, p): self.host, self.port = h, p
    def set_path(self, p):         self.path = p
    def set_query(self, q):        self.query = q
    def set_fragment(self, f):     self.fragment = f
    def set_opaque(self, o):       self.opaque = o

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
```

---

## **11. URI Object**

```text
class URIObject:
    def __init__(scheme, username, password, host, port, path, query, fragment, opaque):
        self.scheme   = scheme
        self.username = username
        self.password = password
        self.host     = host
        self.port     = port
        self.path     = path
        self.query    = query
        self.fragment = fragment
        self.opaque   = opaque

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
```


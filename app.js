import { connect } from 'cloudflare:sockets';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Read all configuration strictly from env (.env / .dev.vars / Cloudflare Secrets)
    const proxyHost = env.PROXY_HOST;
    const proxyPort = env.PROXY_PORT ? parseInt(env.PROXY_PORT, 10) : 0;
    
    // Resolve Proxy Authorization: from PROXY_AUTH or PROXY_USERNAME + PROXY_PASSWORD
    let proxyAuth = env.PROXY_AUTH;
    if (!proxyAuth && env.PROXY_USERNAME && env.PROXY_PASSWORD) {
      proxyAuth = "Basic " + btoa(`${env.PROXY_USERNAME}:${env.PROXY_PASSWORD}`);
    }

    const targetBase = env.TARGET_UPSTREAM_URL || env.NGROK_URL;
    const token = env.NGROK_AUTHTOKEN;

    // 1. CORS Preflight handling
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
          "Access-Control-Allow-Headers": "*",
        },
      });
    }

    // 2. Browser Root Check & Diagnostics (GET only on /)
    // Runs before proxy validation so the status check always responds with 200 OK
    if ((url.pathname === "/" || url.pathname === "") && request.method === "GET") {
      return new Response(
        JSON.stringify({
          status: "ONLINE",
          message: "Gateway Proxy is Active",
          upstream_configured: Boolean(targetBase),
          proxy_configured: Boolean(proxyHost && proxyAuth),
          timestamp: new Date().toISOString()
        }, null, 2),
        {
          status: 200,
          headers: { 
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
          }
        }
      );
    }

    // 3. Validate environment configuration for outbound proxy calls
    const missingConfigs = [];
    if (!proxyHost) missingConfigs.push("PROXY_HOST");
    if (!proxyPort) missingConfigs.push("PROXY_PORT");
    if (!proxyAuth) missingConfigs.push("PROXY_AUTH (or PROXY_USERNAME & PROXY_PASSWORD)");
    if (!targetBase) missingConfigs.push("TARGET_UPSTREAM_URL or NGROK_URL");

    if (missingConfigs.length > 0) {
      return new Response(
        JSON.stringify({
          status: "CONFIG_ERROR",
          message: "Required environment configuration is missing on Cloudflare. Run 'npm run push-secrets' to sync .env secrets to Cloudflare.",
          missing_count: missingConfigs.length
        }, null, 2),
        {
          status: 500,
          headers: { 
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
          }
        }
      );
    }

    // 4. IP Check Endpoint (Verify Webshare Static IP without leaking IP publicly)
    if (url.pathname === "/test-ip") {
      try {
        const testRes = await fetchViaProxy(
          "https://ipv4.webshare.io/", 
          { method: "GET" }, 
          { host: proxyHost, port: proxyPort, auth: proxyAuth }
        );
        const ipText = await testRes.text();
        const outboundIp = ipText.trim();
        const isMatched = outboundIp === proxyHost;
        return new Response(
          JSON.stringify({ 
            status: "SUCCESS",
            proxy_verified: isMatched,
            timestamp: new Date().toISOString()
          }, null, 2), 
          {
            status: 200,
            headers: { 
              "Content-Type": "application/json",
              "Access-Control-Allow-Origin": "*"
            }
          }
        );
      } catch (e) {
        return new Response(
          JSON.stringify({ 
            status: "ERROR", 
            error: "Proxy connection check failed" 
          }, null, 2), 
          { 
            status: 500,
            headers: { 
              "Content-Type": "application/json",
              "Access-Control-Allow-Origin": "*"
            }
          }
        );
      }
    }

    // 5. Construct Target URL (forward path & search query)
    const targetUrl = targetBase.replace(/\/$/, "") + url.pathname + url.search;

    // 6. Headers sanitize & Ngrok credentials inject
    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("cf-connecting-ip");
    headers.delete("cf-ray");
    headers.delete("cf-visitor");
    headers.delete("cf-worker");
    headers.delete("x-forwarded-for");
    headers.delete("x-forwarded-proto");
    headers.delete("x-real-ip");
    
    // Ngrok free warning bypass & authentication headers
    headers.set("ngrok-skip-browser-warning", "true");
    if (token) {
      headers.set("ngrok-agent-token", token);
    }

    try {
      const bodyData = ["GET", "HEAD"].includes(request.method) ? null : await request.arrayBuffer();

      // Request Webshare Static Proxy ke through Ngrok ko forward hogi
      const response = await fetchViaProxy(
        targetUrl, 
        {
          method: request.method,
          headers: headers,
          body: bodyData,
        },
        { host: proxyHost, port: proxyPort, auth: proxyAuth }
      );

      const responseHeaders = new Headers(response.headers);
      responseHeaders.set("Access-Control-Allow-Origin", "*");
      responseHeaders.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS");
      responseHeaders.set("Access-Control-Allow-Headers", "*");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ 
          error: "Gateway forwarding error", 
          status: 502
        }, null, 2), 
        {
          status: 502,
          headers: { 
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
          },
        }
      );
    }
  },
};

// Webshare HTTP CONNECT Tunnel implementation
async function fetchViaProxy(targetUrl, options, proxyConfig) {
  const { host, port, auth } = proxyConfig;

  const target = new URL(targetUrl);
  const targetPort = target.port || (target.protocol === "https:" ? 443 : 80);

  // 1. Raw TCP socket open karein Webshare proxy ke sath
  const socket = connect(`${host}:${port}`);

  // 2. Proxy CONNECT handshake
  const connectPayload = 
    `CONNECT ${target.hostname}:${targetPort} HTTP/1.1\r\n` +
    `Host: ${target.hostname}:${targetPort}\r\n` +
    `Proxy-Authorization: ${auth}\r\n` +
    `User-Agent: Cloudflare-Worker-Proxy\r\n\r\n`;

  const writer = socket.writable.getWriter();
  await writer.write(new TextEncoder().encode(connectPayload));
  writer.releaseLock();

  // 3. Handshake response verify karein
  const reader = socket.readable.getReader();
  let buffer = "";
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) throw new Error("Proxy connection closed during handshake");
    buffer += decoder.decode(value, { stream: true });
    if (buffer.includes("\r\n\r\n")) break;
  }

  const [headerPart] = buffer.split("\r\n\r\n");
  if (!headerPart.includes("200")) {
    throw new Error(`Proxy CONNECT failed: ${headerPart.split("\r\n")[0]}`);
  }
  reader.releaseLock();

  // 4. Target host (Ngrok / API) ke sath TLS handshake
  const tlsSocket = target.protocol === "https:" 
    ? socket.startTls({ expectedServerHostname: target.hostname }) 
    : socket;

  // 5. HTTP Payload forward karein
  const tlsWriter = tlsSocket.writable.getWriter();
  const reqMethod = options.method || "GET";
  let requestHeaders = `${reqMethod} ${target.pathname + target.search} HTTP/1.1\r\n`;

  const reqHeaders = new Headers(options.headers || {});
  reqHeaders.set("Host", target.hostname);
  reqHeaders.set("Connection", "close");
  reqHeaders.delete("keep-alive");
  reqHeaders.delete("transfer-encoding");

  if (options.body) {
    reqHeaders.set("Content-Length", options.body.byteLength.toString());
  } else {
    reqHeaders.delete("content-length");
  }

  for (const [key, val] of reqHeaders.entries()) {
    requestHeaders += `${key}: ${val}\r\n`;
  }
  requestHeaders += `\r\n`;

  await tlsWriter.write(new TextEncoder().encode(requestHeaders));
  if (options.body) {
    await tlsWriter.write(options.body);
  }
  tlsWriter.releaseLock();

  // 6. Direct response stream parse karein
  return parseRawHttpResponse(tlsSocket.readable);
}

// HTTP Response parser with chunked transfer decoding support
async function parseRawHttpResponse(readableStream) {
  const reader = readableStream.getReader();
  let headerBuffer = new Uint8Array(0);
  let headerString = "";
  let bodyStartIndex = -1;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const merged = new Uint8Array(headerBuffer.length + value.length);
    merged.set(headerBuffer);
    merged.set(value, headerBuffer.length);
    headerBuffer = merged;

    const text = new TextDecoder().decode(headerBuffer);
    const splitIndex = text.indexOf("\r\n\r\n");
    if (splitIndex !== -1) {
      headerString = text.slice(0, splitIndex);
      bodyStartIndex = new TextEncoder().encode(headerString + "\r\n\r\n").length;
      break;
    }
  }

  const lines = headerString.split("\r\n");
  const statusLine = lines[0] || "HTTP/1.1 200 OK";
  const statusCode = parseInt(statusLine.split(" ")[1], 10) || 200;
  const statusText = statusLine.split(" ").slice(2).join(" ") || "OK";

  const resHeaders = new Headers();
  for (let i = 1; i < lines.length; i++) {
    const idx = lines[i].indexOf(":");
    if (idx !== -1) {
      resHeaders.append(lines[i].slice(0, idx).trim(), lines[i].slice(idx + 1).trim());
    }
  }

  const isChunked = (resHeaders.get("transfer-encoding") || "").toLowerCase().includes("chunked");
  resHeaders.delete("transfer-encoding");
  resHeaders.delete("connection");
  resHeaders.delete("keep-alive");

  const initialBody = headerBuffer.slice(bodyStartIndex);
  let responseBody;

  if (isChunked) {
    responseBody = decodeChunkedStream(reader, initialBody);
  } else {
    responseBody = new ReadableStream({
      async start(controller) {
        if (initialBody.length > 0) controller.enqueue(initialBody);
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          controller.enqueue(value);
        }
        controller.close();
      }
    });
  }

  return new Response(responseBody, {
    status: statusCode,
    statusText: statusText,
    headers: resHeaders,
  });
}

// Decode HTTP/1.1 chunked transfer encoding stream
function decodeChunkedStream(reader, initialBytes) {
  let buffer = initialBytes || new Uint8Array(0);

  function concat(a, b) {
    const res = new Uint8Array(a.length + b.length);
    res.set(a, 0);
    res.set(b, a.length);
    return res;
  }

  function findCrlf(buf) {
    for (let i = 0; i < buf.length - 1; i++) {
      if (buf[i] === 0x0d && buf[i + 1] === 0x0a) {
        return i;
      }
    }
    return -1;
  }

  return new ReadableStream({
    async pull(controller) {
      while (true) {
        const crlfIndex = findCrlf(buffer);
        if (crlfIndex === -1) {
          const { value, done } = await reader.read();
          if (done) {
            if (buffer.length > 0) controller.enqueue(buffer);
            controller.close();
            return;
          }
          buffer = concat(buffer, value);
          continue;
        }

        const sizeLine = new TextDecoder().decode(buffer.slice(0, crlfIndex)).trim();
        const chunkSize = parseInt(sizeLine.split(";")[0], 16);
        if (isNaN(chunkSize)) {
          if (buffer.length > 0) controller.enqueue(buffer);
          controller.close();
          return;
        }

        if (chunkSize === 0) {
          controller.close();
          return;
        }

        const chunkStart = crlfIndex + 2;
        const chunkEnd = chunkStart + chunkSize;

        while (buffer.length < chunkEnd + 2) {
          const { value, done } = await reader.read();
          if (done) {
            if (buffer.length > chunkStart) {
              controller.enqueue(buffer.slice(chunkStart));
            }
            controller.close();
            return;
          }
          buffer = concat(buffer, value);
        }

        const chunkData = buffer.slice(chunkStart, chunkEnd);
        controller.enqueue(chunkData);
        buffer = buffer.slice(chunkEnd + 2);
        return;
      }
    }
  });
}

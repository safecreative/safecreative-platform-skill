# Webhooks

Endpoints are configured in the console (HTTPS, public address), each with the event types it receives and its secret
(`whsec_…`). Every delivery is a `POST` with a JSON envelope:

```json
{
  "id": "ntc_kfyf2sqproqjvxzduhak",
  "type": "certification.completed",
  "created_at": "2026-10-23T09:09:04.271241Z",
  "mode": "test",
  "data": { "certification_id": "CERT-TEST-2026-0000004", "channel_id": "ch_…", "status": "completed",
            "event_count": 2, "verification_code": "SC-TEST-2026-MWLY-C2DA" }
}
```

Types: `certification.completed`, `certification.failed`, `balance.low`, `balance.exhausted`,
`events.unpaid_limit_reached`, `consumption.limit_reached`, `recharge.auto_completed`, `recharge.auto_failed`,
`webhook.test`. The `data` fields of each are in the API reference (`Webhook…Data` schemas). New fields may be added:
ignore unknown ones.

Headers: `X-SC-Signature: v1=<hex>`, `X-SC-Timestamp` (Unix seconds), `X-SC-Webhook-Id` (the envelope `id`, the same on
every retry).

## Handling a delivery

1. Read the **raw body bytes** before any JSON parsing (frameworks that re-serialize the body break the signature).
2. `expected = hex(HMAC-SHA256(secret, X-SC-Timestamp + "." + raw body))`; compare with the hex after `v1=` in **constant
   time**.
3. Reject if the timestamp is more than 5 minutes away from now.
4. De-duplicate by `X-SC-Webhook-Id` (store processed ids).
5. Answer any `2xx` quickly and do the work asynchronously. Failed deliveries are retried after 1 min, 5 min, 30 min, 2 h,
   6 h, 12 h and 24 h; an endpoint that keeps failing is disabled and the owner is emailed.

## Python

```python
import hashlib, hmac, time

def verify_sc_webhook(secret: str, timestamp: str, signature: str, raw_body: bytes, tolerance: int = 300) -> bool:
    if not signature.startswith("v1=") or not timestamp.isdigit() or abs(time.time() - int(timestamp)) > tolerance:
        return False
    expected = hmac.new(secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[3:])
```

## TypeScript (Node)

```ts
import { createHmac, timingSafeEqual } from "node:crypto";

export function verifyScWebhook(secret: string, timestamp: string, signature: string, rawBody: Buffer, toleranceSeconds = 300): boolean {
  if (!signature.startsWith("v1=") || !/^\d+$/.test(timestamp)) return false;
  if (Math.abs(Date.now() / 1000 - Number(timestamp)) > toleranceSeconds) return false;
  const expected = createHmac("sha256", secret).update(`${timestamp}.`).update(rawBody).digest("hex");
  const received = signature.slice(3);
  return expected.length === received.length && timingSafeEqual(Buffer.from(expected), Buffer.from(received));
}

// Express: keep the raw body for this route.
// app.post("/webhooks/safecreative", express.raw({ type: "application/json" }), (req, res) => {
//   const ok = verifyScWebhook(process.env.SC_WEBHOOK_SECRET!, req.get("X-SC-Timestamp") ?? "",
//                              req.get("X-SC-Signature") ?? "", req.body);
//   if (!ok) return res.sendStatus(401);
//   res.sendStatus(204);                       // then process JSON.parse(req.body) asynchronously
// });
```

## Java (17+)

```java
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

public final class ScWebhooks {
    public static boolean verify(String secret, String timestamp, String signature, byte[] rawBody) throws Exception {
        if (signature == null || !signature.startsWith("v1=") || timestamp == null || !timestamp.matches("\\d+")) {
            return false;
        }
        if (Math.abs(System.currentTimeMillis() / 1000 - Long.parseLong(timestamp)) > 300) {
            return false;
        }
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        mac.update((timestamp + ".").getBytes(StandardCharsets.UTF_8));
        byte[] expected = mac.doFinal(rawBody);
        byte[] received;
        try {
            received = HexFormat.of().parseHex(signature.substring(3));
        } catch (IllegalArgumentException e) {
            return false;
        }
        return MessageDigest.isEqual(expected, received);
    }
}
```

Command-line check of a captured delivery: `scripts/sc_verify_webhook.py`.

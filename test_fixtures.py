"""
Sample log fixtures for prompt validation and integration testing.

Three representative failure types covering the main categories used
to validate SYSTEM_PROMPT quality in WO-009 and the LLM integration in WO-010.
"""

# ── Fixture 1: Java NullPointerException stack trace ──────────────────────
JAVA_NPE_LOG = """\
2024-03-15 14:23:07.891 ERROR [main] c.e.s.OrderService - Failed to process order 98712
java.lang.NullPointerException: Cannot invoke "com.example.model.Customer.getAddress()" because "customer" is null
    at com.example.service.OrderService.validateShipping(OrderService.java:87)
    at com.example.service.OrderService.processOrder(OrderService.java:54)
    at com.example.controller.OrderController.submitOrder(OrderController.java:32)
    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
    at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
    at java.lang.reflect.Method.invoke(Method.java:498)
2024-03-15 14:23:07.892 WARN  [main] c.e.s.OrderService - Order 98712 rolled back
2024-03-15 14:23:07.893 INFO  [main] c.e.c.OrderController - Returning 500 to client for order 98712
"""

# ── Fixture 2: HTTP timeout / connection refused ───────────────────────────
HTTP_TIMEOUT_LOG = """\
2024-03-15 09:45:01.123 INFO  [worker-3] c.e.c.PaymentClient - Initiating payment request to https://payments.internal/charge
2024-03-15 09:45:01.124 DEBUG [worker-3] c.e.c.PaymentClient - POST /charge timeout=5000ms
2024-03-15 09:45:06.125 ERROR [worker-3] c.e.c.PaymentClient - Connection timed out after 5000ms: payments.internal:443
    java.net.SocketTimeoutException: Read timed out
        at java.net.SocketInputStream.socketRead0(Native Method)
        at java.net.SocketInputStream.socketRead(SocketInputStream.java:116)
        at com.example.client.PaymentClient.charge(PaymentClient.java:141)
        at com.example.service.CheckoutService.completePayment(CheckoutService.java:78)
2024-03-15 09:45:06.126 WARN  [worker-3] c.e.c.PaymentClient - Retry 1/3 in 1000ms
2024-03-15 09:45:07.127 ERROR [worker-3] c.e.c.PaymentClient - Connection refused: payments.internal:443
    java.net.ConnectException: Connection refused (Connection refused)
        at java.net.PlainSocketImpl.socketConnect(Native Method)
        at com.example.client.PaymentClient.charge(PaymentClient.java:141)
2024-03-15 09:45:07.128 ERROR [worker-3] c.e.s.CheckoutService - Payment service unreachable after 3 attempts; order 55231 failed
"""

# ── Fixture 3: Linux permission denied / auth failure ─────────────────────
PERMISSION_DENIED_LOG = """\
Mar 15 22:10:03 prod-worker-02 sshd[14892]: Failed password for deploy from 10.0.1.45 port 52341 ssh2
Mar 15 22:10:03 prod-worker-02 sshd[14892]: error: maximum authentication attempts exceeded for deploy from 10.0.1.45 port 52341 ssh2 [preauth]
Mar 15 22:10:03 prod-worker-02 sshd[14892]: Disconnecting authenticating user deploy 10.0.1.45 port 52341: Too many authentication failures [preauth]
Mar 15 22:10:05 prod-worker-02 deploy-agent[9921]: FATAL: Unable to connect to prod-worker-02 via SSH
Mar 15 22:10:05 prod-worker-02 deploy-agent[9921]: subprocess.CalledProcessError: Command '['ssh', '-i', '/home/ci/.ssh/deploy_rsa', 'deploy@prod-worker-02', 'ls /app']' returned non-zero exit status 255
Mar 15 22:10:05 prod-worker-02 deploy-agent[9921]: Deployment pipeline ABORTED — target host unreachable
Mar 15 22:10:05 prod-worker-02 sudo[9930]: deploy : user NOT in sudoers ; TTY=unknown ; PWD=/home/deploy ; USER=root ; COMMAND=/bin/systemctl restart app
Mar 15 22:10:05 prod-worker-02 kernel: [UFW BLOCK] IN=eth0 OUT= MAC=... SRC=10.0.1.45 DST=10.0.2.10 LEN=60 PROTO=TCP DPT=22
"""

# Hero snippet recommendation (best demo log for live presentation)
# JAVA_NPE_LOG produces the most impressive output because:
# - Clear single root cause traceable to a specific line
# - Named class/method hierarchy provides specific evidence citations
# - Remediation is concrete and immediately actionable
HERO_SNIPPET = JAVA_NPE_LOG
HERO_SNIPPET_DESCRIPTION = (
    "Java NullPointerException — single clear root cause, specific line reference, "
    "concrete remediation steps. Best for live demo."
)

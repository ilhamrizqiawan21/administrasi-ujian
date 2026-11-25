export interface BridgeError {
  code: string;
  message: string;
  retryable: boolean;
}

export type BridgeResponse<T> =
  | { ok: true; request_id: string; data: T }
  | { ok: false; request_id: string; error: BridgeError };

interface PyWebViewApi {
  invoke: (request: {
    method: string;
    request_id: string;
    payload: Record<string, unknown>;
  }) => Promise<BridgeResponse<unknown>>;
}

declare global {
  interface Window {
    pywebview?: {
      api?: PyWebViewApi;
    };
  }
}

function waitForPyWebView(timeoutMs = 3000): Promise<PyWebViewApi> {
  if (window.pywebview?.api?.invoke) {
    return Promise.resolve(window.pywebview.api);
  }

  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      window.removeEventListener("pywebviewready", onReady);
      reject(
        new Error(
          "Bridge native PyWebView tidak tersedia (jalankan melalui aplikasi desktop)."
        )
      );
    }, timeoutMs);

    function onReady() {
      if (window.pywebview?.api?.invoke) {
        window.clearTimeout(timer);
        window.removeEventListener("pywebviewready", onReady);
        resolve(window.pywebview.api);
      }
    }

    window.addEventListener("pywebviewready", onReady);
  });
}

export async function invokeBridge<T>(
  method: string,
  payload: Record<string, unknown> = {}
): Promise<T> {
  const requestId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `req-${Date.now()}`;

  if (import.meta.env.DEV && !window.pywebview?.api?.invoke) {
    const { invokeDevMock } = await import("./mockBridge");
    const mockResponse = (await invokeDevMock(
      method,
      requestId,
      payload
    )) as BridgeResponse<T>;
    if (!mockResponse.ok) {
      throw new Error(
        `${mockResponse.error.code}: ${mockResponse.error.message}`
      );
    }
    return mockResponse.data;
  }

  const api = await waitForPyWebView();
  const response = (await api.invoke({
    method,
    request_id: requestId,
    payload,
  })) as BridgeResponse<T>;

  if (!response.ok) {
    throw new Error(`${response.error.code}: ${response.error.message}`);
  }
  return response.data;
}

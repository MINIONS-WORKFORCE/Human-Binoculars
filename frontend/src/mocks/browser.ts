import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);

export function startMocking() {
  return worker.start({
    serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` },
    // Only complain about API calls nobody mocked, not about scripts and images.
    // (MSW 3 renamed onUnhandledRequest to onUnhandledFrame.)
    onUnhandledFrame({ frame, defaults }) {
      const request = (frame.data as { request?: Request }).request;
      if (request && new URL(request.url).pathname.startsWith("/api/"))
        defaults.warn();
    },
  });
}

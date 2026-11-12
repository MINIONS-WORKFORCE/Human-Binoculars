// The same handlers that run in the browser answer every fetch in Vitest.
import { afterAll, afterEach, beforeAll } from "vitest";
import { setupServer } from "msw/node";
import { handlers } from "../mocks/handlers";

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

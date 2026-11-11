import { apiBase } from "../config";
import { createApiClient } from "./client";

export * from "./client";
export const api = createApiClient(apiBase);

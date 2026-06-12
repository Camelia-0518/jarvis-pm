/**
 * Dev-only logger — suppresses logs in production builds.
 *
 * Usage:
 *   import { devLog, devWarn, devError } from "@/utils/logger";
 *   devLog("debug info", data);
 *   devWarn("something unexpected", reason);
 *   devError("operation failed", error);
 */

const isDev = typeof process !== "undefined" && process.env.NODE_ENV === "development";

function noop(..._args: unknown[]): void {}

export const devLog: (...args: unknown[]) => void = isDev ? console.log.bind(console, "[DEV]") : noop;

export const devWarn: (...args: unknown[]) => void = isDev ? console.warn.bind(console, "[DEV]") : noop;

export const devError: (...args: unknown[]) => void = isDev ? console.error.bind(console, "[DEV]") : noop;

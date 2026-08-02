import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { afterEach, vi } from "vitest";

vi.stubGlobal("scrollTo", vi.fn());
configure({ asyncUtilTimeout: 30_000 });
afterEach(() => cleanup());

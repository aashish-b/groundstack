import { loadSession } from "./api";

export async function bootstrap(): Promise<void> {
  await loadSession();
}

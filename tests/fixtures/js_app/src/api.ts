import { refreshToken } from "./auth";

export async function loadSession(): Promise<string> {
  const session = await refreshToken("token");
  return session.accessToken;
}

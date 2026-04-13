export interface Session {
  accessToken: string;
}

export async function refreshToken(refreshToken: string): Promise<Session> {
  const response = await fetch("/api/refresh", {
    method: "POST",
    body: JSON.stringify({ refreshToken }),
  });
  return response.json();
}

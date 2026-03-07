import { type NextRequest, NextResponse } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  const { supabaseResponse, user, supabase } = await updateSession(request);
  const { pathname } = request.nextUrl;

  // Public routes: login, auth callback, static assets
  const publicPaths = ["/login", "/auth/callback"];
  if (publicPaths.some((p) => pathname.startsWith(p))) {
    return supabaseResponse;
  }

  // No user → redirect to /login
  if (!user) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Fetch role from usuarios table
  const { data: usuario } = await supabase
    .from("usuarios")
    .select("rol")
    .eq("id", user.id)
    .single();

  const role = usuario?.rol ?? "pendiente";

  // Pendiente users can only see /pendiente
  if (role === "pendiente" && !pathname.startsWith("/pendiente")) {
    return NextResponse.redirect(new URL("/pendiente", request.url));
  }

  // Approved users should not see /pendiente
  if (role !== "pendiente" && pathname.startsWith("/pendiente")) {
    return NextResponse.redirect(new URL("/app", request.url));
  }

  // Admin-only routes
  if (pathname.startsWith("/app/admin") && role !== "admin") {
    return NextResponse.redirect(new URL("/app", request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};

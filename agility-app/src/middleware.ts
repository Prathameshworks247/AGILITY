export { default } from "next-auth/middleware";

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/developer-dashboard",
    "/project/:path*",
    "/sprint/:path*",
    "/create-org",
  ],
};


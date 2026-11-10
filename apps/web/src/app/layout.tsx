import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORHEX — Your World. Understood.",
  description:
    "A personal intelligence workspace connecting persistent memory, helpful AI, and read-only Sui insights.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

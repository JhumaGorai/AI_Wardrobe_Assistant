import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Wardrobe",
  description: "Your digital wardrobe and personal AI stylist.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}

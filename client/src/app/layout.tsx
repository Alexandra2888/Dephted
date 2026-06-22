import type { Metadata } from "next";
import { DM_Sans, Space_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "depthed",
  description: "learn by going deeper_",
  icons: { icon: "/favicon.svg" },
};

const dmsans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dmsans",
  weight: ["400", "500", "600", "700"],
});

const spaceMono = Space_Mono({
  subsets: ["latin"],
  variable: "--font-space-mono",
  weight: ["400", "700"],
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${dmsans.variable} ${spaceMono.variable}`}>
      <body className="min-h-screen bg-background text-foreground font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

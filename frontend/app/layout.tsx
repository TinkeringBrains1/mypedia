import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Mypedia | Learn with clarity",
  description: "Personalised learning that meets each student where they are.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

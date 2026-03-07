import type { Metadata } from "next";
import { Lato, Poppins } from "next/font/google";
import "./globals.css";

const lato = Lato({
  subsets: ["latin"],
  weight: ["300", "400", "700", "900"],
  variable: "--font-lato",
  display: "swap",
});

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-poppins",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Debt Tracker | Unergy",
  description: "Plataforma interna de seguimiento de deudas y covenants",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${lato.variable} ${poppins.variable}`}>
      <body className="font-body antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}

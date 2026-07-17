import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Bangladesh NID Extractor | AI-Powered ID Card Reader",
  description:
    "Extract structured information from Bangladesh National ID cards using a hybrid OCR + Vision AI pipeline. Supports Bengali and English text.",
  keywords: ["Bangladesh NID", "ID card reader", "OCR", "AI extraction", "NID extractor"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-gray-50 text-gray-800 antialiased">
        {/* Top navigation bar */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
            {/* Bangladesh flag colors: green and red */}
            <div className="flex items-center gap-1.5 shrink-0">
              <div className="w-5 h-3.5 rounded-sm overflow-hidden flex">
                <div className="w-1/2 bg-green-700" />
                <div className="w-1/2 bg-green-700 relative flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-red-600 absolute left-0 translate-x-[-35%]" />
                </div>
              </div>
            </div>
            <span className="text-sm font-semibold text-gray-800">
              NID Extractor
            </span>
            <span className="text-gray-300 text-xs">|</span>
            <span className="text-xs text-gray-500">
              OCR + Vision AI Pipeline
            </span>
          </div>
        </header>

        {children}

        {/* Footer */}
        <footer className="border-t border-gray-200 bg-white mt-auto">
          <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
            <p className="text-xs text-gray-400">
              Bangladesh NID Extractor · IDLC TAP Project
            </p>
            <p className="text-xs text-gray-400">
              Powered by PaddleOCR + OpenRouter
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}

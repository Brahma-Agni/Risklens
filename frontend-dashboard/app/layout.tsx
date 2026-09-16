import type { Metadata } from 'next';
import { Geist_Mono, Space_Grotesk } from 'next/font/google';
import './globals.css';

const spaceGrotesk = Space_Grotesk({
  variable: '--font-space-grotesk',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000',
  ),
  title: 'RiskLens — Risk Operations Command Center',
  description:
    'Real-time payment risk intelligence, coordinated abuse detection, and analyst investigation workflows.',
  openGraph: {
    title: 'RiskLens',
    description: 'Risk Operations Command Center',
    images: ['/risklens-og.png'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'RiskLens',
    description: 'Risk Operations Command Center',
    images: ['/risklens-og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${spaceGrotesk.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

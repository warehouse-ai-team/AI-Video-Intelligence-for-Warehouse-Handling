import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Warehouse AI Dashboard',
  description: 'AI video intelligence for warehouse handling — supervisor console',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
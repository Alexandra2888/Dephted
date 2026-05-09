import { DepthedLogo } from "@/components/logo"

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="mb-10">
        <DepthedLogo variant="wordmark-tagline" theme="dark" />
      </div>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  )
}

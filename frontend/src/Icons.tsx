// Inline icon set. Stroke-based, 16x16 viewBox, inheriting `currentColor` so a
// single icon works on every surface and in both themes without duplicate assets.

interface IconProps {
  className?: string;
}

const base = {
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: "false" as const,
};

export function ShieldIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M8 1.75 13 3.5v4c0 3.2-2.1 5.9-5 6.75-2.9-.85-5-3.55-5-6.75v-4L8 1.75Z" />
      <path d="M6 7.75 7.4 9.2 10.2 6.4" />
    </svg>
  );
}

export function SearchIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="7.25" cy="7.25" r="4.25" />
      <path d="m10.5 10.5 2.75 2.75" />
    </svg>
  );
}

export function UploadIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M8 10.5V2.75" />
      <path d="m5 5.75 3-3 3 3" />
      <path d="M2.75 10v2.25c0 .55.45 1 1 1h8.5c.55 0 1-.45 1-1V10" />
    </svg>
  );
}

export function ReportIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M9 1.75H4.25c-.55 0-1 .45-1 1v10.5c0 .55.45 1 1 1h7.5c.55 0 1-.45 1-1V5.5L9 1.75Z" />
      <path d="M8.75 2v3.25H12" />
      <path d="M5.75 9.25h4.5M5.75 11.5h3" />
    </svg>
  );
}

export function CommandIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M5.5 3.5a2 2 0 1 0 0 4h5a2 2 0 1 1 0 4 2 2 0 0 1-2-2v-5a2 2 0 1 0-4 0v5a2 2 0 1 1-2 2 2 2 0 0 1 2-2h5a2 2 0 1 0 0-4h-4Z" />
    </svg>
  );
}

export function SunIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1.5v1.25M8 13.25v1.25M14.5 8h-1.25M2.75 8H1.5M12.6 3.4l-.9.9M4.3 11.7l-.9.9M12.6 12.6l-.9-.9M4.3 4.3l-.9-.9" />
    </svg>
  );
}

export function MoonIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M13.25 9.4A5.5 5.5 0 0 1 6.6 2.75a5.75 5.75 0 1 0 6.65 6.65Z" />
    </svg>
  );
}

export function SignOutIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M6 13.25H3.75c-.55 0-1-.45-1-1V3.75c0-.55.45-1 1-1H6" />
      <path d="M10.25 11 13.25 8l-3-3" />
      <path d="M13.25 8h-7" />
    </svg>
  );
}

export function InboxIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M2.25 9.5h3l1 2h3.5l1-2h3" />
      <path d="M4.4 2.75h7.2c.44 0 .83.29.96.71l1.19 4.04c.03.09.05.19.05.29v4.46c0 .55-.45 1-1 1H3.2c-.55 0-1-.45-1-1V7.79c0-.1.02-.2.05-.29L3.44 3.46a1 1 0 0 1 .96-.71Z" />
    </svg>
  );
}

export function AlertIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M8 5.5v3.25" />
      <path d="M8 11.4h.01" />
      <path d="M7.13 2.4 1.9 11.4a1 1 0 0 0 .87 1.5h10.46a1 1 0 0 0 .87-1.5L8.87 2.4a1 1 0 0 0-1.74 0Z" />
    </svg>
  );
}

export function CloseIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="m4.25 4.25 7.5 7.5M11.75 4.25l-7.5 7.5" />
    </svg>
  );
}

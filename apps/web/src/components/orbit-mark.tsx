import type { SVGProps } from "react";

export function OrbitMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
      {...props}
    >
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3" />
      <circle cx="12" cy="12" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="17" cy="7" r="2.4" fill="#17222d" />
      <circle cx="17" cy="7" r="2" />
      <circle cx="17" cy="7" r="0.55" fill="currentColor" stroke="none" />
      <circle cx="7" cy="17" r="2.4" fill="#17222d" />
      <circle cx="7" cy="17" r="2" />
      <circle cx="7" cy="17" r="0.55" fill="currentColor" stroke="none" />
    </svg>
  );
}

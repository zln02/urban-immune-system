/**
 * IBM Carbon 스타일 16px 스트로크 아이콘 세트.
 * 외부 의존성 없이 inline SVG — 번들 크기 관리 + 색맹 팔레트 일관성.
 */

import type { SVGProps } from "react";

interface IconProps extends Omit<SVGProps<SVGSVGElement>, "stroke" | "fill"> {
  size?: number;
  stroke?: string;
  fill?: string;
  sw?: number;
  children?: React.ReactNode;
}

function Icon({ size = 16, fill = "none", stroke = "currentColor", sw = 1.5, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill={fill}
      stroke={stroke}
      strokeWidth={sw}
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const I = {
  Alert: (p: IconProps) => (
    <Icon {...p}>
      <path d="M8 1.5 L14.5 13.5 H1.5 Z" />
      <path d="M8 6 V9.5" />
      <circle cx="8" cy="11.5" r="0.6" fill="currentColor" stroke="none" />
    </Icon>
  ),
  Check: (p: IconProps) => <Icon {...p}><path d="M2.5 8.5 L6 12 L13.5 4" /></Icon>,
  Chevron: (p: IconProps) => <Icon {...p}><path d="M4 3 L10 8 L4 13" /></Icon>,
  ChevronDown: (p: IconProps) => <Icon {...p}><path d="M3 5 L8 10 L13 5" /></Icon>,
  Download: (p: IconProps) => (
    <Icon {...p}>
      <path d="M8 2 V11" />
      <path d="M4.5 7.5 L8 11 L11.5 7.5" />
      <path d="M2 13.5 H14" />
    </Icon>
  ),
  Filter: (p: IconProps) => <Icon {...p}><path d="M2 3 H14 L10 8 V13 L6 11 V8 Z" /></Icon>,
  Grid: (p: IconProps) => (
    <Icon {...p}>
      <rect x="2" y="2" width="5" height="5" />
      <rect x="9" y="2" width="5" height="5" />
      <rect x="2" y="9" width="5" height="5" />
      <rect x="9" y="9" width="5" height="5" />
    </Icon>
  ),
  Home: (p: IconProps) => <Icon {...p}><path d="M2 8 L8 2.5 L14 8 V13.5 H10 V9 H6 V13.5 H2 Z" /></Icon>,
  Map: (p: IconProps) => (
    <Icon {...p}>
      <path d="M2 4 L6 2.5 L10 4 L14 2.5 V12 L10 13.5 L6 12 L2 13.5 Z" />
      <path d="M6 2.5 V12" />
      <path d="M10 4 V13.5" />
    </Icon>
  ),
  Report: (p: IconProps) => (
    <Icon {...p}>
      <path d="M3 1.5 H10 L13 4.5 V14.5 H3 Z" />
      <path d="M10 1.5 V4.5 H13" />
      <path d="M5.5 8 H10.5" />
      <path d="M5.5 11 H10.5" />
    </Icon>
  ),
  Settings: (p: IconProps) => (
    <Icon {...p}>
      <circle cx="8" cy="8" r="2.5" />
      <path d="M8 1.5 V4 M8 12 V14.5 M1.5 8 H4 M12 8 H14.5 M3.3 3.3 L5 5 M11 11 L12.7 12.7 M12.7 3.3 L11 5 M5 11 L3.3 12.7" />
    </Icon>
  ),
  Shield: (p: IconProps) => <Icon {...p}><path d="M8 1.5 L13.5 3.5 V8 C13.5 11.5 11 13.5 8 14.5 C5 13.5 2.5 11.5 2.5 8 V3.5 Z" /></Icon>,
  Pharmacy: (p: IconProps) => (
    <Icon {...p}>
      <rect x="2.5" y="2.5" width="11" height="11" />
      <path d="M8 5 V11" />
      <path d="M5 8 H11" />
    </Icon>
  ),
  Water: (p: IconProps) => <Icon {...p}><path d="M8 1.5 C4 6 3 9 3 11 C3 13 5.2 14.5 8 14.5 C10.8 14.5 13 13 13 11 C13 9 12 6 8 1.5 Z" /></Icon>,
  Search: (p: IconProps) => (
    <Icon {...p}>
      <circle cx="7" cy="7" r="4.5" />
      <path d="M10.3 10.3 L14 14" />
    </Icon>
  ),
  Bell: (p: IconProps) => (
    <Icon {...p}>
      <path d="M4 12 V8 C4 5.2 5.8 3 8 3 C10.2 3 12 5.2 12 8 V12" />
      <path d="M3 12 H13" />
      <path d="M6.5 14 C6.5 14.8 7.2 15.5 8 15.5 C8.8 15.5 9.5 14.8 9.5 14" />
    </Icon>
  ),
  Print: (p: IconProps) => (
    <Icon {...p}>
      <path d="M4 6 V2 H12 V6" />
      <rect x="2" y="6" width="12" height="6" />
      <path d="M4 10 H12 V14 H4 Z" />
    </Icon>
  ),
  Close: (p: IconProps) => <Icon {...p}><path d="M3 3 L13 13 M13 3 L3 13" /></Icon>,
};

export type IconName = keyof typeof I;

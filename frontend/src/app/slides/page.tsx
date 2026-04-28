import { redirect } from "next/navigation";

// 정적 슬라이드 덱 (public/slides/index.html) 으로 영구 리다이렉트.
// 단일 진입점: /slides → /slides/index.html
export default function SlidesEntry() {
  redirect("/slides/index.html");
}

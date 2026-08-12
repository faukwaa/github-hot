import { marked } from "marked";

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** 渲染结果安全过滤：移除脚本/内联事件，相对图片拼接 GitHub raw 地址 */
function sanitizeHtml(html: string, imgBase: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc
    .querySelectorAll("script, iframe, object, embed, style, link, meta")
    .forEach((el) => el.remove());
  doc.querySelectorAll("*").forEach((el) => {
    [...el.attributes].forEach((attr) => {
      if (/^on/i.test(attr.name)) el.removeAttribute(attr.name);
    });
    if (el.tagName === "A" && /^\s*javascript:/i.test(el.getAttribute("href") || "")) {
      el.removeAttribute("href");
    }
    if (el.tagName === "IMG") {
      const src = el.getAttribute("src") || "";
      if (src && !/^https?:|^data:|^#/.test(src)) {
        el.setAttribute("src", `${imgBase}/${src}`);
      }
    }
  });
  return doc.body.innerHTML;
}

/** marked（GitHub README 同源引擎）+ 安全过滤；
 *  与 GitHub 对齐：不开启 breaks（软换行折叠为空格，徽章行不折行），
 *  代码块显示语言标签。 */
export function renderMarkdown(md: string | null, fullName: string): string {
  if (!md || !md.trim()) return '<p class="text-muted-foreground">（无内容）</p>';
  const imgBase = `https://raw.githubusercontent.com/${fullName}/HEAD`;
  try {
    const renderer = new marked.Renderer();
    renderer.image = ({ href, title, text }) => {
      const url = /^https?:|^data:|^#/.test(href) ? href : `${imgBase}/${href}`;
      const alt = text ? ` alt="${text.replace(/"/g, "&quot;")}"` : "";
      const ttl = title ? ` title="${title.replace(/"/g, "&quot;")}"` : "";
      return `<img src="${url}"${alt}${ttl} loading="lazy">`;
    };
    renderer.code = ({ text, lang }) => {
      const label = lang ? `<span class="md-lang">${esc(lang)}</span>` : "";
      return `<pre>${label}<code>${text}</code></pre>`;
    };
    const html = marked.parse(md, { gfm: true, renderer, async: false }) as string;
    return sanitizeHtml(html, imgBase);
  } catch {
    const html = marked.parse(md, { gfm: true, async: false }) as string;
    return sanitizeHtml(html, imgBase);
  }
}

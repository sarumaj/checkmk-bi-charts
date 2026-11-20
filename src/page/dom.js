// Helpers for the page's elements.

export const $ = (id) => document.getElementById(id);

export function el(tag, props, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children);
  return node;
}

export const css = (name) => getComputedStyle(document.body).getPropertyValue(name).trim();

export function message(text, isError) {
  $("msg").textContent = text || "";
  $("msg").classList.toggle("err", Boolean(isError));
}

const DONUTS = [
  { id: "boston-cream-donut", name: "Boston Cream Donut", price: 2.09, calories: 240, seasonal: false, img: "img/boston-cream-donut.webp" },
  { id: "biscoff-boston-cream", name: "Biscoff Boston Cream", price: 2.39, calories: 310, seasonal: true, img: "img/biscoff-boston-cream.webp" },
  { id: "spiced-vanilla-filled-ring-donut", name: "Spiced Vanilla Filled Ring Donut", price: 2.39, calories: 320, seasonal: true, img: "img/spiced-vanilla-filled-ring-donut.webp" },
  { id: "6-assorted-donuts", name: "6 Assorted Donuts", price: 9.39, calories: 1860, seasonal: false, img: "img/6-assorted-donuts.webp" },
  { id: "12-assorted-donuts", name: "12 Assorted Donuts", price: 17.39, calories: 3720, seasonal: false, img: "img/12-assorted-donuts.webp" },
  { id: "canada-celebration-donut", name: "Canada Celebration Donut", price: 2.39, calories: 290, seasonal: false, img: "img/canada-celebration-donut.webp" },
  { id: "apple-fritter-donut", name: "Apple Fritter Donut", price: 2.09, calories: 330, seasonal: false, img: "img/apple-fritter-donut.webp" },
  { id: "honey-cruller-donut", name: "Honey Cruller Donut", price: 2.09, calories: 320, seasonal: false, img: "img/honey-cruller-donut.webp" },
  { id: "old-fashioned-plain-donut", name: "Old Fashioned Plain Donut", price: 2.09, calories: 280, seasonal: false, img: "img/old-fashioned-plain-donut.webp" },
  { id: "chocolate-dip-donut", name: "Chocolate Dip Donut", price: 2.09, calories: 220, seasonal: false, img: "img/chocolate-dip-donut.webp" },
  { id: "sour-cream-glazed-donut", name: "Sour Cream Glazed Donut", price: 2.09, calories: 340, seasonal: false, img: "img/sour-cream-glazed-donut.webp" },
  { id: "chocolate-glazed-donut", name: "Chocolate Glazed Donut", price: 2.09, calories: 330, seasonal: false, img: "img/chocolate-glazed-donut.webp" },
  { id: "vanilla-dip-donut", name: "Vanilla Dip Donut", price: 2.09, calories: 250, seasonal: false, img: "img/vanilla-dip-donut.webp" },
  { id: "honey-dip-donut", name: "Honey Dip Donut", price: 2.09, calories: 250, seasonal: false, img: "img/honey-dip-donut.webp" },
  { id: "double-chocolate-donut", name: "Double Chocolate Donut", price: 2.09, calories: 310, seasonal: false, img: "img/double-chocolate-donut.webp" },
  { id: "toasted-coconut-donut", name: "Toasted Coconut Donut", price: 2.09, calories: 360, seasonal: false, img: "img/toasted-coconut-donut.webp" }
];

function renderMenu() {
  const grid = document.getElementById("donut-grid");
  if (!grid) return;
  grid.innerHTML = DONUTS.map(d => `
    <article class="card">
      <div class="card-img"><img src="${d.img}" alt="${d.name}" loading="lazy" width="280" height="280"></div>
      <h3>${d.name}${d.seasonal ? ' <span class="badge">Limited time</span>' : ''}</h3>
      <p class="price">$${d.price.toFixed(2)} CAD <span class="cal">${d.calories} cal</span></p>
    </article>
  `).join("");
}

document.addEventListener("DOMContentLoaded", renderMenu);

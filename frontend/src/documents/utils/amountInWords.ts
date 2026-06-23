const BELOW_20 = [
  "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
  "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
  "Seventeen", "Eighteen", "Nineteen",
];
const TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

function chunk(n: number): string {
  if (n < 20) return BELOW_20[n];
  if (n < 100) return `${TENS[Math.floor(n / 10)]}${n % 10 ? ` ${BELOW_20[n % 10]}` : ""}`.trim();
  if (n < 1000) {
    return `${BELOW_20[Math.floor(n / 100)]} Hundred${n % 100 ? ` ${chunk(n % 100)}` : ""}`.trim();
  }
  return "";
}

function wholeToWords(n: number): string {
  if (n === 0) return "";
  const millions = Math.floor(n / 1_000_000);
  const thousands = Math.floor((n % 1_000_000) / 1000);
  const remainder = n % 1000;
  const parts: string[] = [];
  if (millions) parts.push(`${chunk(millions)} Million`);
  if (thousands) parts.push(`${chunk(thousands)} Thousand`);
  if (remainder) parts.push(chunk(remainder));
  return parts.join(" ");
}

export function amountInWords(amount: number, currency = "Dollars"): string {
  const whole = Math.floor(Math.abs(amount));
  const cents = Math.round((Math.abs(amount) - whole) * 100);
  if (whole === 0 && cents === 0) return `Zero ${currency} Only`;

  let result = wholeToWords(whole) || "Zero";
  result += ` ${currency}`;
  if (cents > 0) result += ` and ${chunk(cents)} Cents`;
  return `${result} Only`;
}

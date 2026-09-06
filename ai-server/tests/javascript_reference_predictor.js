const fs = require("fs");

const request = JSON.parse(fs.readFileSync(0, "utf8"));
const model = JSON.parse(fs.readFileSync(request.modelPath, "utf8"));

function sigmoid(score) {
  if (score >= 0) {
    const z = Math.exp(-score);
    return 1 / (1 + z);
  }
  const z = Math.exp(score);
  return z / (1 + z);
}

function predict(vector) {
  let raw = 0;
  for (const tree of model.trees) {
    const [featureIndex, categorical, threshold, defaultLeft, missingTypeValue, leftLeaf, rightLeaf] = tree;
    const value = vector[featureIndex];
    const missingType = Number(missingTypeValue);
    const missing = value === null || Number.isNaN(value);
    let left;
    if (categorical) {
      if (missing) left = false;
      else {
        const category = Number(value);
        left = category >= 0 && threshold.map(Number).includes(category);
      }
    } else {
      const numericValue = missing && missingType !== 1 ? 0 : Number(value);
      if ((missingType === 1 && missing) || (missingType === 2 && numericValue === 0)) {
        left = Boolean(defaultLeft);
      } else {
        left = numericValue <= Number(threshold);
      }
    }
    raw += left ? Number(leftLeaf) : Number(rightLeaf);
  }
  return sigmoid(raw);
}

function topRiskPercent(c3) {
  const quantiles = model.c3_quantiles;
  let low = 0;
  let high = quantiles.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (Number(quantiles[middle]) <= c3) low = middle + 1;
    else high = middle;
  }
  const index = Math.max(0, low - 1);
  const value = (1 - index / (quantiles.length - 1)) * 100;
  return Math.round(Math.max(0.001, value) * 10000) / 10000;
}

function grade(c3) {
  if (c3 >= model.grade_thresholds["경고"]) return "WARNING";
  if (c3 >= model.grade_thresholds["주의"]) return "CAUTION";
  if (c3 >= model.grade_thresholds["관심"]) return "INTEREST";
  return "NORMAL";
}

const hazards = request.vectors.map(predict);
const predictions = [];
for (let index = 0; index < hazards.length; index += 3) {
  const monthly = hazards.slice(index, index + 3);
  const c3 = 1 - monthly.reduce((survival, hazard) => survival * (1 - hazard), 1);
  predictions.push({c3, grade: grade(c3), topRiskPercent: topRiskPercent(c3)});
}
process.stdout.write(JSON.stringify({hazards, predictions}));

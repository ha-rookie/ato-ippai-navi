import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const configPath = path.join(repoRoot, "ops", "weekly-verifiers.json");
const config = JSON.parse(fs.readFileSync(configPath, "utf8"));

test("weekly verifier set is unique and covers the current MVP verifier groups", () => {
  assert.equal(config.include.length, 17);

  const workflows = config.include.map((item) => item.workflow);
  assert.equal(new Set(workflows).size, workflows.length);

  const required = [
    "poc-nagoya-open-data.yml",
    "poc-tsurumai-open-data.yml",
    "poc-meijo-meiko-open-data.yml",
    "poc-meiko-kanayama-transfer.yml",
    "poc-sakuradori-walk-hubs.yml",
    "poc-kamiida-heiandori-transfer.yml",
    "poc-meitetsu-seto-sakaemachi.yml",
    "poc-meitetsu-main-nagoya.yml",
    "poc-meitetsu-tokoname-nagoya.yml",
    "verify-meitetsu-inuyama-production.yml",
    "poc-meitetsu-chikko-oe-transfer.yml",
    "poc-meitetsu-komaki-ajima.yml",
    "poc-aonami-nagoya.yml",
    "poc-kintetsu-nagoya.yml",
    "poc-jr-kansai-nagoya.yml",
    "poc-jr-chuo-nagoya.yml",
    "poc-jr-tokaido-nagoya.yml"
  ];

  assert.deepEqual([...workflows].sort(), [...required].sort());
});

test("every scheduled child workflow supports workflow_dispatch and checks production JSON", () => {
  for (const item of config.include) {
    assert.ok(item.label, item);
    assert.ok(!item.workflow.startsWith("apply-"), item);
    assert.ok(!item.workflow.startsWith("smoke-"), item);

    const workflowPath = path.join(repoRoot, ".github", "workflows", item.workflow);
    assert.ok(fs.existsSync(workflowPath), `${item.workflow} must exist`);

    const source = fs.readFileSync(workflowPath, "utf8");
    assert.match(source, /\n\s*workflow_dispatch:\s*\n/, item.workflow);
    assert.match(source, /src\/data\/last-trains-nagoya\.json/, item.workflow);
  }
});

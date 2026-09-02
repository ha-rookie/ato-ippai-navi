import test from "node:test";
import assert from "node:assert/strict";
import {
  DESTINATION_STATION_STORAGE_KEY,
  loadDestinationStation,
  normalizeDestinationStation,
  saveDestinationStation
} from "../public/js/settings.js";

function memoryStorage() {
  const values = new Map();

  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    }
  };
}

test("destination station accepts supported Higashiyama and Tsurumai codes", () => {
  assert.equal(normalizeDestinationStation("h1"), "H01");
  assert.equal(normalizeDestinationStation("H22"), "H22");
  assert.equal(normalizeDestinationStation("t1"), "T01");
  assert.equal(normalizeDestinationStation("T15"), "T15");
  assert.equal(normalizeDestinationStation("T20"), "T20");

  assert.throws(
    () => normalizeDestinationStation("H23"),
    /H01-H22 or T01-T20/
  );
  assert.throws(
    () => normalizeDestinationStation("T21"),
    /H01-H22 or T01-T20/
  );
  assert.throws(
    () => normalizeDestinationStation("M05"),
    /H01-H22 or T01-T20/
  );
});

test("selected destination is stored and restored locally", () => {
  const storage = memoryStorage();

  assert.equal(loadDestinationStation(storage), null);

  assert.equal(
    saveDestinationStation("H18", storage),
    "H18"
  );
  assert.equal(
    storage.getItem(DESTINATION_STATION_STORAGE_KEY),
    "H18"
  );
  assert.equal(loadDestinationStation(storage), "H18");
});

test("invalid stored destination is ignored", () => {
  const storage = memoryStorage();
  storage.setItem(DESTINATION_STATION_STORAGE_KEY, "H99");

  assert.equal(loadDestinationStation(storage), null);
});

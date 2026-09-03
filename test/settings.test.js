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

test("destination station accepts supported subway line codes", () => {
  assert.equal(normalizeDestinationStation("h1"), "H01");
  assert.equal(normalizeDestinationStation("H22"), "H22");
  assert.equal(normalizeDestinationStation("t1"), "T01");
  assert.equal(normalizeDestinationStation("T15"), "T15");
  assert.equal(normalizeDestinationStation("T20"), "T20");
  assert.equal(normalizeDestinationStation("m1"), "M01");
  assert.equal(normalizeDestinationStation("M28"), "M28");
  assert.equal(normalizeDestinationStation("e2"), "E02");
  assert.equal(normalizeDestinationStation("E07"), "E07");
  assert.equal(normalizeDestinationStation("s1"), "S01");
  assert.equal(normalizeDestinationStation("S21"), "S21");
  assert.equal(normalizeDestinationStation("k1"), "K01");
  assert.equal(normalizeDestinationStation("st1"), "ST01");
  assert.equal(normalizeDestinationStation("ST12"), "ST12");
  assert.equal(normalizeDestinationStation("an1"), "AN01");
  assert.equal(normalizeDestinationStation("AN11"), "AN11");
  assert.equal(normalizeDestinationStation("kt-e1"), "KT-E01");
  assert.equal(normalizeDestinationStation("KT-E07"), "KT-E07");

  assert.throws(
    () => normalizeDestinationStation("H23"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("T21"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("M29"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("E08"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("S22"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("K02"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("ST13"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("AN12"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("KT-E08"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
  );
  assert.throws(
    () => normalizeDestinationStation("KT01"),
    /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, AN01-AN11, or KT-E01-KT-E07/
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

  assert.equal(
    saveDestinationStation("st12", storage),
    "ST12"
  );
  assert.equal(loadDestinationStation(storage), "ST12");

  assert.equal(saveDestinationStation("an9", storage), "AN09");
  assert.equal(loadDestinationStation(storage), "AN09");

  assert.equal(saveDestinationStation("kt-e7", storage), "KT-E07");
  assert.equal(loadDestinationStation(storage), "KT-E07");
});

test("invalid stored destination is ignored", () => {
  const storage = memoryStorage();
  storage.setItem(DESTINATION_STATION_STORAGE_KEY, "H99");

  assert.equal(loadDestinationStation(storage), null);
});

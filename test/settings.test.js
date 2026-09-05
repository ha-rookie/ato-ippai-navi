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

const DESTINATION_ERROR_PATTERN =
  /H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, K01, ST01-ST12, NH24-NH38, TA01-TA05, IY02-IY03, CH01, AN01-AN11, KT-E01-KT-E07, JR-CJ00-JR-CJ02, JR-CF01-JR-CF06, or JR-CA62-JR-CA68/;

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
  assert.equal(normalizeDestinationStation("jr-cj0"), "JR-CJ00");
  assert.equal(normalizeDestinationStation("JR-CJ2"), "JR-CJ02");

  for (const invalid of [
    "H23",
    "T21",
    "M29",
    "E08",
    "S22",
    "K02",
    "ST13",
    "AN12",
    "KT-E08",
    "KT01"
  ]) {
    assert.throws(
      () => normalizeDestinationStation(invalid),
      DESTINATION_ERROR_PATTERN
    );
  }

  assert.throws(
    () => normalizeDestinationStation("JR-CJ03"),
    /JR-CJ00-JR-CJ02/
  );
  assert.throws(
    () => normalizeDestinationStation("CJ01"),
    /JR-CJ00-JR-CJ02/
  );
  assert.throws(
    () => normalizeDestinationStation("JRCJ01"),
    /JR-CJ00-JR-CJ02/
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

  assert.equal(saveDestinationStation("jr-cj2", storage), "JR-CJ02");
  assert.equal(loadDestinationStation(storage), "JR-CJ02");
});

test("invalid stored destination is ignored", () => {
  const storage = memoryStorage();
  storage.setItem(DESTINATION_STATION_STORAGE_KEY, "H99");

  assert.equal(loadDestinationStation(storage), null);
});

test("destination station accepts JR Chuo namespaced station codes", () => {
  assert.equal(normalizeDestinationStation("jr-cf1"), "JR-CF01");
  assert.equal(normalizeDestinationStation("JR-CF6"), "JR-CF06");
  assert.throws(() => normalizeDestinationStation("JR-CF00"));
  assert.throws(() => normalizeDestinationStation("JR-CF07"));
  assert.throws(() => normalizeDestinationStation("CF01"));
});

test("JR Chuo destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("jr-cf6", storage), "JR-CF06");
  assert.equal(loadDestinationStation(storage), "JR-CF06");
});


test("destination station accepts JR Tokaido namespaced station codes", () => {
  assert.equal(normalizeDestinationStation("jr-ca62"), "JR-CA62");
  assert.equal(normalizeDestinationStation("JR-CA68"), "JR-CA68");
  assert.throws(() => normalizeDestinationStation("JR-CA61"));
  assert.throws(() => normalizeDestinationStation("JR-CA69"));
  assert.throws(() => normalizeDestinationStation("CA62"));
});

test("JR Tokaido destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("jr-ca62", storage), "JR-CA62");
  assert.equal(loadDestinationStation(storage), "JR-CA62");
});


test("destination station accepts Meitetsu Main NH24-NH38 codes", () => {
  assert.equal(normalizeDestinationStation("nh24"), "NH24");
  assert.equal(normalizeDestinationStation("NH38"), "NH38");
  assert.throws(() => normalizeDestinationStation("NH23"), /NH24-NH38/);
  assert.throws(() => normalizeDestinationStation("NH39"), /NH24-NH38/);
});

test("Meitetsu Main destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("nh34", storage), "NH34");
  assert.equal(loadDestinationStation(storage), "NH34");
});


test("destination station accepts Meitetsu Tokoname TA01-TA05 codes", () => {
  assert.equal(normalizeDestinationStation("ta1"), "TA01");
  assert.equal(normalizeDestinationStation("TA05"), "TA05");
  assert.throws(() => normalizeDestinationStation("TA00"), /TA01-TA05/);
  assert.throws(() => normalizeDestinationStation("TA06"), /TA01-TA05/);
});

test("Meitetsu Tokoname destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("ta3", storage), "TA03");
  assert.equal(loadDestinationStation(storage), "TA03");
});


test("destination station accepts Meitetsu Inuyama IY02-IY03 codes", () => {
  assert.equal(normalizeDestinationStation("iy2"), "IY02");
  assert.equal(normalizeDestinationStation("IY03"), "IY03");
  assert.throws(() => normalizeDestinationStation("IY01"), /IY02-IY03/);
  assert.throws(() => normalizeDestinationStation("IY04"), /IY02-IY03/);
});

test("Meitetsu Inuyama destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("iy3", storage), "IY03");
  assert.equal(loadDestinationStation(storage), "IY03");
});


test("destination station accepts Meitetsu Chikko CH01 code", () => {
  assert.equal(normalizeDestinationStation("ch1"), "CH01");
  assert.equal(normalizeDestinationStation("CH01"), "CH01");
  assert.throws(() => normalizeDestinationStation("CH02"), /CH01/);
});

test("Meitetsu Chikko destination is stored and restored locally", () => {
  const storage = memoryStorage();
  assert.equal(saveDestinationStation("ch1", storage), "CH01");
  assert.equal(loadDestinationStation(storage), "CH01");
});

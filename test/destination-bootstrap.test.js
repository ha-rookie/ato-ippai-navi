import test from "node:test";
import assert from "node:assert/strict";

import { prepareDestinationSelect } from "../public/js/destination-bootstrap.js";

function makeDocument() {
  const h22 = {
    value: "H22",
    textContent: "H22 藤が丘",
    disabled: false,
    selected: true
  };

  const select = {
    options: [h22],
    firstChild: h22,
    value: "H22",
    focused: false,
    insertBefore(option) {
      this.options.unshift(option);
      this.firstChild = option;
    },
    focus() {
      this.focused = true;
    }
  };

  const routeBadge = { textContent: "深夜帰宅判定 → 藤が丘" };
  const status = { textContent: "" };
  const clickListeners = [];
  const checkButton = {
    addEventListener(type, listener, capture) {
      if (type === "click") clickListeners.push({ listener, capture });
    }
  };

  const elements = {
    destinationCode: select,
    routeBadge,
    status,
    checkButton
  };

  const documentRef = {
    getElementById(id) {
      return elements[id] || null;
    },
    createElement(tagName) {
      assert.equal(tagName, "option");
      return {
        value: "",
        textContent: "",
        disabled: false,
        selected: false
      };
    }
  };

  return { documentRef, select, routeBadge, status, clickListeners };
}

test("unset destination replaces arbitrary H22 default with explicit placeholder", () => {
  const fixture = makeDocument();
  prepareDestinationSelect(fixture.documentRef);

  assert.equal(fixture.select.value, "");
  assert.equal(fixture.select.options[0].value, "");
  assert.equal(fixture.select.options[0].textContent, "選択してください");
  assert.equal(fixture.select.options[0].disabled, true);
  assert.equal(fixture.select.options[0].selected, true);
  assert.equal(fixture.routeBadge.textContent, "深夜帰宅判定 → 最寄り駅");
});

test("check is blocked until a destination is selected", () => {
  const fixture = makeDocument();
  prepareDestinationSelect(fixture.documentRef);

  assert.equal(fixture.clickListeners.length, 1);
  assert.equal(fixture.clickListeners[0].capture, true);

  let prevented = false;
  let stopped = false;
  fixture.clickListeners[0].listener({
    preventDefault() {
      prevented = true;
    },
    stopImmediatePropagation() {
      stopped = true;
    }
  });

  assert.equal(prevented, true);
  assert.equal(stopped, true);
  assert.equal(fixture.status.textContent, "帰宅先の最寄り駅を選択してください");
  assert.equal(fixture.select.focused, true);

  fixture.select.value = "H22";
  prevented = false;
  stopped = false;
  fixture.clickListeners[0].listener({
    preventDefault() {
      prevented = true;
    },
    stopImmediatePropagation() {
      stopped = true;
    }
  });

  assert.equal(prevented, false);
  assert.equal(stopped, false);
});

import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

test("tonight decision keeps train result when taxi routing fails", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (_url, options) => {
    const body = JSON.parse(options.body);

    if (body.travelMode === "WALK") {
      const destination = body.destination?.address || "";
      const isHisayaodori = destination.includes("久屋大通");

      return new Response(
        JSON.stringify({
          routes: [{
            distanceMeters: isHisayaodori ? 331 : 719,
            duration: isHisayaodori ? "271s" : "589s"
          }]
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" }
        }
      );
    }

    if (body.travelMode === "DRIVE") {
      return new Response(
        JSON.stringify({
          error: {
            message: "temporary routing failure"
          }
        }),
        {
          status: 400,
          headers: { "content-type": "application/json" }
        }
      );
    }

    throw new Error(`unexpected travelMode: ${body.travelMode}`);
  };

  try {
    const request = new Request(
      "https://example.test/api/tonight-decision",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          origin: {
            latitude: 35.1715,
            longitude: 136.9057
          },
          departureTime: "2026-09-04T23:30:00+09:00",
          dayType: "weekday",
          destinationCode: "S21",
          offsetMinutes: [0, 30],
          stationBufferMinutes: 3,
          minimumBoardingLeadMinutes: 1,
          includeDispatchFee: true
        })
      }
    );

    const response = await worker.fetch(request, {
      GOOGLE_MAPS_API_KEY: "test-key"
    });
    const data = await response.json();

    assert.equal(response.status, 200, data);
    assert.equal(data.destinationCode, "S21");
    assert.equal(data.destinationName, "徳重");

    assert.deepEqual(
      Object.keys(data.train.walkOptions).sort(),
      ["hisayaodori", "marunouchi"]
    );

    assert.equal(data.scenarios[0].recommendedMode, "train");
    assert.equal(
      data.scenarios[0].recommendedOriginId,
      "hisayaodori"
    );
    assert.equal(data.scenarios[0].lastDeparture, "23:56");

    assert.equal(data.taxi.routeFound, false);
    assert.match(
      data.taxi.error,
      /Google Routes API 400/
    );

    assert.equal(data.scenarios[1].recommendedMode, "unknown");
    assert.equal(data.scenarios[1].status, "unavailable");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

import test from "node:test";
import assert from "node:assert/strict";
import { composeTonightDecision } from "../src/tonight.js";

test("train is recommended while reachable, taxi after last train", () => {
  const result = composeTonightDecision(
    {
      scenarios: [
        {
          offsetMinutes: 0,
          canReachDestination: true,
          nextTrain: "23:32",
          lastTrain: "00:02",
          estimatedDestinationStationArrivalTime:
            "2026-09-04T14:53:00.000Z",
          localDestinationStationArrivalTime: "23:53"
        },
        {
          offsetMinutes: 60,
          leaveTime: "2026-09-04T15:20:00.000Z",
          canReachDestination: false,
          nextTrain: null,
          lastTrain: "00:02"
        }
      ]
    },
    {
      routeFound: true,
      durationSeconds: 1227,
      estimatedTotalYen: 8080
    }
  );

  assert.equal(result.destinationScope, "station_only");
  assert.equal(result.scenarios[0].recommendedMode, "train");
  assert.equal(result.scenarios[0].status, "train_available");
  assert.equal(result.scenarios[0].taxiEstimatedTotalYen, 8080);
  assert.equal(
    result.scenarios[0].localDestinationStationArrivalTime,
    "23:53"
  );

  assert.equal(result.scenarios[1].recommendedMode, "taxi");
  assert.equal(result.scenarios[1].status, "taxi_fallback");
  assert.equal(result.scenarios[1].taxiEstimatedTotalYen, 8080);
  assert.equal(result.scenarios[1].taxiTravelMinutes, 21);
  assert.equal(
    result.scenarios[1].localDestinationStationArrivalTime,
    "00:41"
  );
});

test("unknown is returned when neither train nor taxi is available", () => {
  const result = composeTonightDecision(
    {
      scenarios: [
        {
          offsetMinutes: 60,
          canReachDestination: false
        }
      ]
    },
    {
      routeFound: false
    }
  );

  assert.equal(result.scenarios[0].recommendedMode, "unknown");
  assert.equal(result.scenarios[0].status, "unavailable");
  assert.equal(result.scenarios[0].taxiEstimatedTotalYen, null);
});


test("last-train boundary data does not invent a train arrival ETA", () => {
  const result = composeTonightDecision(
    {
      dataSource: "internal_last_train_json",
      scenarios: [
        {
          offsetMinutes: 30,
          canReachDestination: true,
          recommendedOriginId: "sakae",
          recommendedOriginName: "栄",
          lastDeparture: "00:02",
          localLastTrainArrivalTime: "00:23",
          estimatedDestinationStationArrivalTime: null,
          localDestinationStationArrivalTime: null,
          arrivalEstimateQuality: "last_train_boundary_only"
        }
      ]
    },
    {
      routeFound: true,
      durationSeconds: 1200,
      estimatedTotalYen: 8000
    }
  );

  assert.equal(result.scenarios[0].recommendedMode, "train");
  assert.equal(
    result.scenarios[0].estimatedDestinationStationArrivalTime,
    null
  );
  assert.equal(
    result.scenarios[0].localDestinationStationArrivalTime,
    null
  );
  assert.equal(
    result.scenarios[0].localLastTrainArrivalTime,
    "00:23"
  );
});

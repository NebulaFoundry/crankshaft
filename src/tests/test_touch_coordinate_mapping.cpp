#include <gtest/gtest.h>

#include "../services/android_auto/TouchCoordinateMapping.h"

using crankshaft::protocol::mapTouchToVideo;

TEST(TouchCoordinateMappingTest, MapsPiTouchSpotifyButtonInto720pVideo) {
  // Reproduced on a Pi 4 / original 800x480 touchscreen: (774,220) hit
  // the map, whereas the equivalent video coordinate opened Spotify.
  EXPECT_EQ(mapTouchToVideo(774, 220, QSize(800, 480), QSize(1280, 720)),
            QPoint(1238, 330));
}

TEST(TouchCoordinateMappingTest, PreservesMatchingResolution) {
  EXPECT_EQ(mapTouchToVideo(774, 220, QSize(800, 480), QSize(800, 480)),
            QPoint(774, 220));
}

TEST(TouchCoordinateMappingTest, UsesUpdatedDisplaySizeWithSameVideoGeometry) {
  EXPECT_EQ(mapTouchToVideo(400, 240, QSize(800, 480), QSize(1280, 720)),
            QPoint(640, 360));
  EXPECT_EQ(mapTouchToVideo(640, 360, QSize(1280, 720), QSize(1280, 720)),
            QPoint(640, 360));
}

TEST(TouchCoordinateMappingTest, ClampsOutOfBoundsInputBeforeScaling) {
  EXPECT_EQ(mapTouchToVideo(-10, -1, QSize(800, 480), QSize(1280, 720)), QPoint(0, 0));
  EXPECT_EQ(mapTouchToVideo(900, 600, QSize(800, 480), QSize(1280, 720)),
            QPoint(1278, 718));
}

TEST(TouchCoordinateMappingTest, HandlesInvalidGeometryWithoutDividingByZero) {
  EXPECT_EQ(mapTouchToVideo(100, 100, QSize(0, 480), QSize(1280, 720)), QPoint());
  EXPECT_EQ(mapTouchToVideo(100, 100, QSize(800, 480), QSize()), QPoint());
}

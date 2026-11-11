#pragma once

#include <QPoint>
#include <QSize>
#include <QtGlobal>

namespace crankshaft::protocol {

// The UI sends pixels in its published display space. Android Auto consumes
// pixels in the video space advertised during service discovery, even when
// the decoded video is resized to fit a smaller physical touchscreen.
inline QPoint mapTouchToVideo(int x, int y, const QSize& displaySize,
                             const QSize& videoSize) {
  if (displaySize.width() <= 0 || displaySize.height() <= 0 ||
      videoSize.width() <= 0 || videoSize.height() <= 0) {
    return QPoint();
  }

  const qint64 boundedX = qBound(0, x, displaySize.width() - 1);
  const qint64 boundedY = qBound(0, y, displaySize.height() - 1);
  return QPoint(static_cast<int>(boundedX * videoSize.width() / displaySize.width()),
                static_cast<int>(boundedY * videoSize.height() / displaySize.height()));
}

}  // namespace crankshaft::protocol

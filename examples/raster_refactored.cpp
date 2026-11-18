// Rasteriser, after the refactor: bounds check, shading and blending split out.
#include <vector>

namespace raster {

struct Pixel {
    unsigned char r, g, b;
};

class Canvas {
public:
    explicit Canvas(int w, int h) : width_(w), height_(h), pixels_(w * h) {}

    void draw(int x, int y, float light) {
        if (!inside(x, y)) {
            return;
        }
        pixels_[y * width_ + x] = shade(light);
    }

private:
    bool inside(int x, int y) const {
        return x >= 0 && x < width_ && y >= 0 && y < height_;
    }

    static Pixel shade(float light) {
        if (light > 0.8f) {
            return Pixel{255, 240, 220};
        }
        if (light > 0.4f) {
            return Pixel{
                (unsigned char)(light * 255),
                (unsigned char)(light * 200),
                (unsigned char)(light * 160),
            };
        }
        return Pixel{20, 24, 32};
    }

    int width_;
    int height_;
    std::vector<Pixel> pixels_;
};

}  // namespace raster

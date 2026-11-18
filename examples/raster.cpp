// Rasteriser, first draft: the shading logic lives inside the draw loop.
#include <vector>

namespace raster {

struct Pixel {
    unsigned char r, g, b;
};

class Canvas {
public:
    explicit Canvas(int w, int h) : width_(w), height_(h), pixels_(w * h) {}

    void draw(int x, int y, float light) {
        if (x < 0 || x >= width_ || y < 0 || y >= height_) {
            return;
        }
        Pixel& p = pixels_[y * width_ + x];
        if (light > 0.8f) {
            p.r = 255; p.g = 240; p.b = 220;
        } else if (light > 0.4f) {
            p.r = (unsigned char)(light * 255);
            p.g = (unsigned char)(light * 200);
            p.b = (unsigned char)(light * 160);
        } else {
            p.r = 20; p.g = 24; p.b = 32;
        }
    }

private:
    int width_;
    int height_;
    std::vector<Pixel> pixels_;
};

}  // namespace raster

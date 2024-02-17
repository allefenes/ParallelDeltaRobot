#include <iostream>
#include <fstream>
#include <cmath>
#include <vector>
#include <chrono>
#include <iomanip>
#include <nlohmann/json.hpp>
#include <windows.h>

using json = nlohmann::json;

using namespace std;

struct forwardResult {

    bool isDefined;

    double Ax_1;
    double Ay_1;
    double Az_1;
    double Bx_1;
    double By_1;
    double Bz_1;
    double Cx_1;
    double Cy_1;
    double Cz_1;
    double BETA_1;
    double FI_1;
    double FI_1_Sec;

    double Ax_2;
    double Ay_2;
    double Az_2;
    double Bx_2;
    double By_2;
    double Bz_2;
    double Cx_2;
    double Cy_2;
    double Cz_2;
    double BETA_2;
    double FI_2;
    double FI_2_Sec;

    double Ax_3;
    double Ay_3;
    double Az_3;
    double Bx_3;
    double By_3;
    double Bz_3;
    double Cx_3;
    double Cy_3;
    double Cz_3;
    double BETA_3;
    double FI_3;
    double FI_3_Sec;


    double Dx;
    double Dy;
    double Dz;

};

struct inverseResult {

    bool isDefined;
    double teta1;
    double teta2;
    double teta3;

};

struct Point {
    double x, y, z;
};

class DeltaRobot {
public:

    const double PI = 3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679;

    DeltaRobot(double la = 64.2,
        double lb = 201,
        double ra = 65,
        double rb = 37.5,
        double btf = 240,
        std::vector<double> alpha = { 0, 120, 240 },
        double minTurnAngle = 0.29296875,
        double ccwMax = -70,
        double cwMax = 150,
        double jointMax = 14
    ) : jointMax(jointMax), cwMax(cwMax), ccwMax(ccwMax), minTurnAngle(minTurnAngle), alpha(alpha), btf(btf), rb(rb), ra(ra), lb(lb), la(la), r(ra - rb) {}

    double degreeToRadian(double degree) const {
        return degree * PI / 180;
    }

    double radianToDegree(double radian) const {
        return radian * 180 / PI;
    }

    forwardResult forwardKinematic(double teta1 = 0, double teta2 = 0, double teta3 = 0) {

        forwardResult result{};

        double tetaRad[3] = { degreeToRadian(teta1), degreeToRadian(teta2), degreeToRadian(teta3) };
        double alphaRad[3] = { degreeToRadian(alpha[0]), degreeToRadian(alpha[1]), degreeToRadian(alpha[2]) };

        double Ax[3]{};
        double Ay[3]{};
        double Az[3]{};
        double Bx[3]{};
        double By[3]{};
        double Bz[3]{};
        double Cx[3]{};
        double Cy[3]{};
        double Cz[3]{};
        double x[3]{};
        double y[3]{};
        double z[3]{};
        double AC[3]{};
        double BETA[3]{};
        double FI[3]{};
        double FI_Sec[3]{};

        for (int i = 0; i < 3; i++) {
            Ax[i] = ra * cos(alphaRad[i]);
            Ay[i] = ra * sin(alphaRad[i]);
            Az[i] = 0;

            Bx[i] = ra * cos(alphaRad[i]) + la * cos(alphaRad[i]) * cos(tetaRad[i]);
            By[i] = ra * sin(alphaRad[i]) + la * sin(alphaRad[i]) * cos(tetaRad[i]);
            Bz[i] = la + sin(tetaRad[i]);

            x[i] = (r + la * cos(tetaRad[i])) * cos(alphaRad[i]);
            y[i] = (r + la * cos(tetaRad[i])) * sin(alphaRad[i]);
            z[i] = la * sin(tetaRad[i]);

        }

        double w1 = pow(x[0], 2) + pow(y[0], 2) + pow(z[0], 2);
        double w2 = pow(x[1], 2) + pow(y[1], 2) + pow(z[1], 2);
        double w3 = pow(x[2], 2) + pow(y[2], 2) + pow(z[2], 2);

        double d1 = (x[1] - x[0]) * (y[2] - y[1]) - (x[2] - x[1]) * (y[1] - y[0]);

        double a1 = ((z[2] - z[1]) * (y[1] - y[0])) - ((z[1] - z[0]) * (y[2] - y[1]));
        double b1 = ((w2 - w1) * (y[2] - y[1]) - (w3 - w2) * (y[1] - y[0])) / 2;

        double d2 = (x[2] - x[1]) * (y[1] - y[0]) - (x[1] - x[0]) * (y[2] - y[1]);
        double a2 = ((z[2] - z[1]) * (x[1] - x[0])) - ((z[1] - z[0]) * (x[2] - x[1]));
        double b2 = ((w2 - w1) * (x[2] - x[1]) - (w3 - w2) * (x[1] - x[0])) / 2;

        double a = (pow(a1, 2) / pow(d1, 2)) + (pow(a2, 2) / pow(d2, 2)) + 1;
        double b = 2 * (((a1 * b1) / pow(d1, 2)) + ((a2 * b2) / pow(d2, 2)) - ((x[0] * a1) / d1) - ((y[0] * a2) / d2) - z[0]);
        double c = (pow(b1, 2) / pow(d1, 2)) + (pow(b2, 2) / pow(d2, 2)) - ((2 * x[0] * b1) / d1) - ((2 * y[0] * b2) / d2) + w1 - pow(lb, 2);

        double Dx;
        double Dy;
        double Dz;


        double delta = pow(b, 2) - (4 * a * c);

        if (delta >= 0) {
            Dz = (-b + sqrt(delta)) / (2 * a);
            Dx = (a1 / d1) * Dz + (b1 / d1);
            Dy = (a2 / d2) * Dz + (b2 / d2);
        }
        else {
            result.isDefined = 0;
            Dx = 0.0;
            Dy = 0.0;
            Dz = 0.0;
        }



        for (int i = 0; i < 3; i++) {
            Cx[i] = Dx + rb * cos(alphaRad[i]);
            Cy[i] = Dy + rb * sin(alphaRad[i]);
            Cz[i] = Dz;
            AC[i] = sqrt(pow((Cx[i] - Ax[i]), 2) + pow((Cy[i] - Ay[i]), 2) + pow((Cz[i] - Az[i]), 2));
            BETA[i] = radianToDegree(acos((pow(la, 2) + pow(lb, 2) - (pow((Cx[i] - Ax[i]), 2) + pow((Cy[i] - Ay[i]), 2) + pow((Cz[i] - Az[i]), 2))) / (2 * la * lb)));
            FI[i] = BETA[i] - radianToDegree(tetaRad[i]);

            double angle = fmod(360 - alpha[i],360);

            angle = degreeToRadian(angle);

            double rotationMatrix[3][3] = {
                                            {cos(angle), -sin(angle), 0},
                                            {sin(angle), cos(angle), 0},
                                            {0, 0, 1}
            };

            double rotatedBx[3]{};
            double rotatedBy[3]{};
            double rotatedBz[3]{};

            rotatedBx[i] = rotationMatrix[0][0] * Bx[i] + rotationMatrix[0][1] * By[i];
            rotatedBy[i] = rotationMatrix[1][0] * Bx[i] + rotationMatrix[1][1] * By[i] ;
            rotatedBz[i] = Bz[i];

            double rotatedCx[3]{};
            double rotatedCy[3]{};
            double rotatedCz[3]{};

            rotatedCx[i] = rotationMatrix[0][0] * Cx[i] + rotationMatrix[0][1] * Cy[i] ;
            rotatedCy[i] = rotationMatrix[1][0] * Cx[i] + rotationMatrix[1][1] * Cy[i] ;
            rotatedCz[i] = Cz[i];

            FI_Sec[i] = radianToDegree(atan2(rotatedCy[i] - rotatedBy[i] , rotatedCz[i] - rotatedBz[i]));
            
        }


        result.isDefined = 1;

        result.Ax_1 = Ax[0];
        result.Ay_1 = Ay[0];
        result.Az_1 = Az[0];
        result.Bx_1 = Bx[0];
        result.By_1 = By[0];
        result.Bz_1 = Bz[0];
        result.Cx_1 = Cx[0];
        result.Cy_1 = Cy[0];
        result.Cz_1 = Cz[0];
        result.BETA_1 = BETA[0];
        result.FI_1 = FI[0];
        result.FI_1_Sec = FI_Sec[0];

        result.Ax_2 = Ax[1];
        result.Ay_2 = Ay[1];
        result.Az_2 = Az[1];
        result.Bx_2 = Bx[1];
        result.By_2 = By[1];
        result.Bz_2 = Bz[1];
        result.Cx_2 = Cx[1];
        result.Cy_2 = Cy[1];
        result.Cz_2 = Cz[1];
        result.BETA_2 = BETA[1];
        result.FI_2 = FI[1];
        result.FI_2_Sec = FI_Sec[1];

        result.Ax_3 = Ax[2];
        result.Ay_3 = Ay[2];
        result.Az_3 = Az[2];
        result.Bx_3 = Bx[2];
        result.By_3 = By[2];
        result.Bz_3 = Bz[2];
        result.Cx_3 = Cx[2];
        result.Cy_3 = Cy[2];
        result.Cz_3 = Cz[2];
        result.BETA_3 = BETA[2];
        result.FI_3 = FI[2];
        result.FI_3_Sec = FI_Sec[2];

        result.Dx = Dx;
        result.Dy = Dy;
        result.Dz = Dz;

        return result;

    }

    inverseResult inverseKinematic(double Dx, double Dy, double Dz) {

        double alphaRad[3] = { degreeToRadian(alpha[0]), degreeToRadian(alpha[1]), degreeToRadian(alpha[2]) };

        inverseResult result{};

        double teta[3]{};
        double X[3]{};
        double cosTeta[3]{};
        double sinTeta[3]{};
        double tteta[3]{};
        for (int i = 0; i < 3; i++) {
            X[i] = (pow(la, 2) - pow(lb, 2) + (pow((Dx - (r * cos(alphaRad[i]))), 2)) + (pow((Dy - (r * sin(alphaRad[i]))), 2)) + pow(Dz, 2)) / (2 * la);

            double A = pow(Dz, 2) + pow(((Dx * cos(alphaRad[i])) + (Dy * sin(alphaRad[i])) - r), 2);
            double B = -2 * X[i] * ((Dx * cos(alphaRad[i])) + (Dy * sin(alphaRad[i])) - r);
            double C = pow(X[i], 2) - pow(Dz, 2);

            double DELTA = pow(B, 2) - (4 * A * C);

            if (DELTA >= 0) {
                cosTeta[i] = (-B + sqrt(DELTA)) / (2 * A);
                sinTeta[i] = (X[i] - ((Dx * cos(alphaRad[i])) + (Dy * sin(alphaRad[i])) - r) * cosTeta[i]) / Dz;
                tteta[i] = atan2(sinTeta[i], cosTeta[i]);
                teta[i] = tteta[i] * 180 / PI;
            }
            else {
                result.isDefined = false;
                result.teta1 = 0;
                result.teta2 = 0;
                result.teta3 = 0;
                return result;
            }
        }

        result.isDefined = true;
        result.teta1 = teta[0];
        result.teta2 = teta[1];
        result.teta3 = teta[2];

        return result;

    }

    double resolution() {
        forwardResult res1 = forwardKinematic(0, 0, 0);
        forwardResult res2 = forwardKinematic(minTurnAngle, 0, 0);

        double x = res1.Dx - res2.Dx;
        double z = res1.Dz - res2.Dz;

        return sqrt(x * x + z * z);

    }

    int calWsAllDots(double iterStep) {
        std::ofstream output("outputAll.json");

        if (output.is_open()) {
            output << "[" << std::endl;
        }
        else {
            std::cout << "File could not be opened!" << std::endl;
        }


        double simArea = ceil(la + lb);

        int dotCounter = 0;

        for (double indexX = -simArea; indexX < simArea; indexX += iterStep) {
            for (double indexY = -simArea; indexY < simArea; indexY += iterStep) {
                for (double indexZ = 0; indexZ < simArea; indexZ += iterStep) {

                    inverseResult resultKinematic = inverseKinematic(indexX, indexY, indexZ);
                    if (resultKinematic.isDefined == true 
                        and resultKinematic.teta1 > cwMax
                        and resultKinematic.teta1 < ccwMax
                        and resultKinematic.teta2 > cwMax
                        and resultKinematic.teta2 < ccwMax
                        and resultKinematic.teta3 > cwMax
                        and resultKinematic.teta3 < ccwMax) {
                        
                            forwardResult phiAngleControl = forwardKinematic(resultKinematic.teta1, resultKinematic.teta2, resultKinematic.teta3);
                            if (abs(phiAngleControl.FI_1_Sec) < jointMax and abs(phiAngleControl.FI_2_Sec) < jointMax and abs(phiAngleControl.FI_3_Sec) < jointMax) {
                                if (dotCounter == 0) {
                                    dotCounter += 1;
                                    output << "[" << indexX << ", " << indexY << ", " << indexZ << "]" << std::endl;
                                }
                                else {
                                    output << ",[" << indexX << ", " << indexY << ", " << indexZ << "]" << std::endl;
                                }
                            }

                    }



                }
            }
        }

        output << "]" << endl;

        output.close();

        return 0;
    }

    int calWsMinSurf(double iterStep) {
        std::ofstream output("outputMinSurf.json");
        if (output.is_open()) {
            output << "[" << std::endl;
        }
        else {
            std::cout << "File could not be opened!" << std::endl;
        }

        double simArea = ceil(la + lb);
        int dotCounter = 0;
        int commaControl = 0;

        for (double indexX = -simArea; indexX < simArea; indexX += iterStep) {
            for (double indexY = -simArea; indexY < simArea; indexY += iterStep) {
                for (double indexZ = 10; indexZ < simArea; indexZ += iterStep) {

                    inverseResult resultKinematic = inverseKinematic(indexX, indexY, indexZ);
                    if (resultKinematic.isDefined == true
                        and resultKinematic.teta1 < cwMax
                        and resultKinematic.teta1 > ccwMax
                        and resultKinematic.teta2 < cwMax
                        and resultKinematic.teta2 > ccwMax
                        and resultKinematic.teta3 < cwMax
                        and resultKinematic.teta3 > ccwMax) {

                        if (dotCounter == 0) {
                            forwardResult phiAngleControl = forwardKinematic(resultKinematic.teta1, resultKinematic.teta2, resultKinematic.teta3);
                            if (abs(phiAngleControl.FI_1_Sec) < jointMax and abs(phiAngleControl.FI_2_Sec) < jointMax and abs(phiAngleControl.FI_3_Sec) < jointMax) {

                                dotCounter += 1;
                                if (commaControl == 0) {
                                    commaControl++;
                                    output << "[" << indexX << ", " << indexY << ", " << indexZ << "]" << std::endl;
                                }
                                else {
                                    output << ",[" << indexX << ", " << indexY << ", " << indexZ << "]" << std::endl;
                                }
                            }
                        }
                        else {
                            dotCounter = 0;
                            break;
                        }
                    }
                }
            }
        }

        output << "]" << endl;

        output.close();

        return 0;
    }

    int calWsMaxSurf(double iterStep) {
        std::ofstream output("outputMaxSurf.json");
        if (output.is_open()) {
            output << "[" << std::endl;
        }
        else {
            std::cout << "File could not be opened!" << std::endl;
        }

        double simArea = ceil(la + lb);
        int dotCounter = 0;
        int commaControl = 0;

        for (double indexX = -simArea; indexX < simArea; indexX += iterStep) {
            for (double indexY = -simArea; indexY < simArea; indexY += iterStep) {
                for (double indexZ = 1.5 * simArea; indexZ > 0; indexZ -= iterStep) {

                    inverseResult resultKinematic = inverseKinematic(indexX, indexY, indexZ);
                    if (resultKinematic.isDefined == true
                        and resultKinematic.teta1 < cwMax
                        and resultKinematic.teta1 > ccwMax
                        and resultKinematic.teta2 < cwMax
                        and resultKinematic.teta2 > ccwMax
                        and resultKinematic.teta3 < cwMax
                        and resultKinematic.teta3 > ccwMax) {

                        if (dotCounter == 0) {
                            forwardResult phiAngleControl = forwardKinematic(resultKinematic.teta1, resultKinematic.teta2, resultKinematic.teta3);
                            if (abs(phiAngleControl.FI_1_Sec) < jointMax and abs(phiAngleControl.FI_2_Sec) < jointMax and abs(phiAngleControl.FI_3_Sec) < jointMax) {
                                dotCounter += 1;
                                if (commaControl == 0) {
                                    commaControl++;
                                    output << "[" << indexX << ", " << indexY << ", " << indexZ << "]" << std::endl;
                                }
                                else {
                                output << ",[" << indexX << ", " << indexY << ", " << indexZ << "]" << std::endl;
                                }
                            }
                        }
                        else {
                            dotCounter = 0;
                            break;
                        }
                    }
                }
            }
        }

        output << "]" << endl;

        output.close();

        return 0;
    }

    double maxMinDotsZ(string fileLoc = "outputMinSurf.json") {
        std::ifstream file(fileLoc);

        if (!file.is_open()) {
            std::cerr << "File could not be opened!" << std::endl;
            return 1;
        }

        json data;
        file >> data;

        double maxZ = -std::numeric_limits<double>::infinity();
        json maxZObject;

        for (const auto& obj : data) {
            double currentZ = obj[2];
            if (currentZ > maxZ) {
                maxZ = currentZ;
                maxZObject = obj;
            }
        }

        file.close();
        return maxZObject[2];
    }

    double maxMaxDotsZ(string fileLoc = "outputMaxSurf.json") {
        std::ifstream file(fileLoc);

        if (!file.is_open()) {
            std::cerr << "File could not be opened!" << std::endl;
            return 1;
        }

        json data;
        file >> data;

        double maxZ = -std::numeric_limits<double>::infinity();
        json maxZObject;

        for (const auto& obj : data) {
            double currentZ = obj[2];
            if (currentZ > maxZ and currentZ < btf) {
                maxZ = currentZ;
                maxZObject = obj;
            }
        }

        file.close();
        return maxZObject[2];
    }

    double calcR(string fileLoc = "outputMaxSurf.json") {

        std::ifstream file(fileLoc);

        if (!file.is_open()) {
            std::cerr << "File could not be opened!" << std::endl;
            return 1;
        }

        json data;
        file >> data;

        double targetZ = DeltaRobot::maxMaxDotsZ(fileLoc);
        double minusX = std::numeric_limits<double>::infinity();
        json minusXObject;

        for (const auto& obj : data) {
            double currentMinusX = obj[0];
            if (currentMinusX < minusX and obj[2] == targetZ) {
                minusX = currentMinusX;
                minusXObject = obj;
            }
        }
        file.close();
        return minusXObject[0];
    }

    int calWs() {

        calWsMaxSurf(resolution());
        calWsMinSurf(resolution());
        /*
        std::ofstream outputCy("outputC.json");

        if (outputCy.is_open()) {
            outputCy << "[" << std::endl;
        }
        else {
            std::cout << "File could not be opened!" << std::endl;
        }

        outputCy << "[" << maxMinDotsZ() << "," << maxMaxDotsZ() << ", " << abs(calcR()) << "]" << std::endl;

        outputCy << "]" << endl;

        outputCy.close();
        */
        return 0;
    }

private:
    double jointMax;
    double cwMax;
    double ccwMax;
    double minTurnAngle;
    std::vector<double> alpha;
    double btf;
    double rb;
    double ra;
    double lb;
    double la;
    double r;
};


int main() {

    DeltaRobot myRobot;

    auto start_time = std::chrono::high_resolution_clock::now();

    forwardResult cozum = myRobot.forwardKinematic(0, 0, 0);
    cout << cozum.Dx << endl;
    cout << cozum.Dy << endl;
    cout << cozum.Dz << endl;

    auto end_time = std::chrono::high_resolution_clock::now();

    auto duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);

    std::cout << "Calculation Chrono: " << duration.count() << " saniye" << std::endl;

    Beep(1000, 1000); // Frekans: 1000 Hz, Süre: 500 ms
     
    return 0;
}





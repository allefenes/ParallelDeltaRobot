// delta_servo_tool: argüman ayrıştırma ve komutların FakeServoBus üzerinde yürütülmesi.
#include <gtest/gtest.h>

#include <sstream>
#include <string>
#include <vector>

#include "delta_edge/servo_tool.hpp"
#include "fake_servo_bus.hpp"

namespace delta_edge::servo_tool {
namespace {

using test::FakeServoBus;
namespace reg = dxl::ax12;

ParseResult parse(const std::vector<std::string>& a) { return parse_args(a); }

std::string parse_error(const std::vector<std::string>& a) {
  const ParseResult r = parse(a);
  EXPECT_FALSE(r.ok);
  return r.error;
}

struct ToolRun {
  int code;
  std::string out;
  std::string err;
};

ToolRun run_on(FakeServoBus& bus, const std::vector<std::string>& argv) {
  const ParseResult p = parse(argv);
  EXPECT_TRUE(p.ok) << p.error;
  std::ostringstream out;
  std::ostringstream err;
  const int code = run(p.args, bus, out, err);
  return {code, out.str(), err.str()};
}

TEST(ServoToolArgs, ParsesCommandsAndOptions) {
  ParseResult r = parse({"scan"});
  ASSERT_TRUE(r.ok);
  EXPECT_EQ(r.args.command, Command::kScan);
  EXPECT_EQ(r.args.scan_from, 0);
  EXPECT_EQ(r.args.scan_to, 253);
  EXPECT_EQ(r.args.baud, 1000000);
  EXPECT_EQ(r.args.device, "");

  r = parse(
      {"--device", "/x/y", "--baud", "57142", "--timeout-ms", "50", "--echo", "scan", "1", "5"});
  ASSERT_TRUE(r.ok);
  EXPECT_EQ(r.args.device, "/x/y");
  EXPECT_EQ(r.args.baud, 57142);
  EXPECT_EQ(r.args.timeout_ms, 50);
  EXPECT_TRUE(r.args.local_echo);
  EXPECT_EQ(r.args.scan_from, 1);
  EXPECT_EQ(r.args.scan_to, 5);

  r = parse({"set-id", "1", "4"});
  ASSERT_TRUE(r.ok);
  EXPECT_EQ(r.args.command, Command::kSetId);
  EXPECT_EQ(r.args.id, 1);
  EXPECT_EQ(r.args.new_id, 4);

  r = parse({"set-baud", "2", "34"});
  ASSERT_TRUE(r.ok);
  EXPECT_EQ(r.args.command, Command::kSetBaud);
  EXPECT_EQ(r.args.baud_code, 34);

  r = parse({"read", "3", "--baud", "1000000"});  // seçenek komuttan sonra da olabilir
  ASSERT_TRUE(r.ok);
  EXPECT_EQ(r.args.command, Command::kRead);
  EXPECT_EQ(r.args.id, 3);

  r = parse({"torque", "2", "on"});
  ASSERT_TRUE(r.ok);
  EXPECT_TRUE(r.args.on);
  r = parse({"torque", "2", "off"});
  ASSERT_TRUE(r.ok);
  EXPECT_FALSE(r.args.on);

  r = parse({"read", "1", "-h"});
  ASSERT_TRUE(r.ok);
  EXPECT_EQ(r.args.command, Command::kHelp);
}

TEST(ServoToolArgs, RejectsBadInput) {
  EXPECT_NE(parse_error({}).find("komut yok"), std::string::npos);
  EXPECT_NE(parse_error({"fly"}).find("bilinmeyen komut"), std::string::npos);
  EXPECT_NE(parse_error({"--fast", "scan"}).find("bilinmeyen seçenek"), std::string::npos);
  EXPECT_NE(parse_error({"scan", "--baud"}).find("bir değer bekliyor"), std::string::npos);
  EXPECT_NE(parse_error({"--baud", "1M", "scan"}).find("--baud"), std::string::npos);
  EXPECT_NE(parse_error({"--baud", "0", "scan"}).find("--baud"), std::string::npos);
  EXPECT_NE(parse_error({"--timeout-ms", "0", "scan"}).find("--timeout-ms"), std::string::npos);
  EXPECT_NE(parse_error({"scan", "3"}).find("2 argüman"), std::string::npos);
  EXPECT_NE(parse_error({"scan", "5", "2"}).find("TO"), std::string::npos);
  EXPECT_NE(parse_error({"set-id", "1"}).find("2 argüman"), std::string::npos);
  EXPECT_NE(parse_error({"set-id", "1", "1"}).find("aynı"), std::string::npos);
  EXPECT_NE(parse_error({"set-id", "1", "254"}).find("NEW"), std::string::npos);  // yayın ID'si
  EXPECT_NE(parse_error({"set-baud", "1", "255"}).find("CODE"), std::string::npos);
  EXPECT_NE(parse_error({"read"}).find("1 argüman"), std::string::npos);
  EXPECT_NE(parse_error({"read", "x"}).find("ID"), std::string::npos);
  EXPECT_NE(parse_error({"read", "1x"}).find("ID"), std::string::npos);
  EXPECT_NE(parse_error({"torque", "1", "yes"}).find("on|off"), std::string::npos);
  EXPECT_NE(std::string(usage()).find("set-baud ID CODE"), std::string::npos);
}

TEST(ServoTool, ScanFindsServos) {
  FakeServoBus bus({1, 2, 3});
  const ToolRun r = run_on(bus, {"scan"});
  EXPECT_EQ(r.code, kExitOk);
  EXPECT_NE(r.out.find("ID 1: model 12"), std::string::npos) << r.out;
  EXPECT_NE(r.out.find("ID 3: model 12"), std::string::npos);
  EXPECT_NE(r.out.find("3 servo bulundu"), std::string::npos);
  int pings = 0;
  for (const auto& in : bus.log()) pings += in.instr == dxl::kPing;
  EXPECT_EQ(pings, 254);  // ID 0..253, yayın ID'si hariç
}

TEST(ServoTool, ScanRangeAndBaudMismatch) {
  FakeServoBus bus({1, 2, 3});
  ToolRun r = run_on(bus, {"scan", "2", "2"});
  EXPECT_EQ(r.code, kExitOk);
  EXPECT_NE(r.out.find("1 servo bulundu"), std::string::npos);
  EXPECT_EQ(r.out.find("ID 1"), std::string::npos);
  bus.set_line_baud(57142);  // servolar 1 Mbps'te: yanıt yok
  r = run_on(bus, {"--baud", "57142", "scan", "0", "10"});
  EXPECT_EQ(r.code, kExitComm);
  EXPECT_NE(r.out.find("0 servo bulundu"), std::string::npos);
}

TEST(ServoTool, ScanReportsServoWithoutModelReply) {
  FakeServoBus bus({5});
  bus.servo(5).table[reg::kStatusReturnLevel] = 0;  // yalnız PING yanıtlanır
  const ToolRun r = run_on(bus, {"scan", "5", "5"});
  EXPECT_EQ(r.code, kExitOk);
  EXPECT_NE(r.out.find("ID 5\n"), std::string::npos) << r.out;
}

TEST(ServoTool, SetIdVerifiesAndRefusesConflicts) {
  FakeServoBus bus({1});
  ToolRun r = run_on(bus, {"set-id", "1", "4"});
  EXPECT_EQ(r.code, kExitOk) << r.err;
  EXPECT_TRUE(bus.has(4));
  EXPECT_FALSE(bus.has(1));
  EXPECT_NE(r.out.find("ID 1 -> 4 tamam"), std::string::npos);

  bus.add_servo(2);
  r = run_on(bus, {"set-id", "4", "2"});
  EXPECT_EQ(r.code, kExitComm);
  EXPECT_NE(r.err.find("zaten kullanımda"), std::string::npos);
  EXPECT_TRUE(bus.has(4));

  r = run_on(bus, {"set-id", "9", "10"});
  EXPECT_EQ(r.code, kExitComm);
  EXPECT_NE(r.err.find("ID 9 yanıt vermiyor"), std::string::npos);
}

TEST(ServoTool, SetIdReportsUnverifiedChange) {
  FakeServoBus bus({1});
  bus.servo(1).table[reg::kStatusReturnLevel] = 2;
  // Yazma ID'yi değiştirmez (EEPROM kilitli gibi): yeni ID doğrulanamaz.
  class NoIdWrite : public SerialPort {
   public:
    explicit NoIdWrite(FakeServoBus& b) : b_(b) {}
    bool write(const std::uint8_t* d, std::size_t n) override {
      if (n > 5 && d[4] == dxl::kWriteData && d[5] == reg::kId) return true;
      return b_.write(d, n);
    }
    std::size_t read(std::uint8_t* x, std::size_t m, int t) override { return b_.read(x, m, t); }
    void flush_input() override { b_.flush_input(); }

   private:
    FakeServoBus& b_;
  } port(bus);
  const ParseResult p = parse({"set-id", "1", "7"});
  std::ostringstream out, err;
  EXPECT_EQ(run(p.args, port, out, err), kExitComm);
  EXPECT_NE(err.str().find("yeni ID 7 doğrulanamadı"), std::string::npos);
}

TEST(ServoTool, SetBaudWritesCodeAndRefusesUnsupported) {
  FakeServoBus bus({1});
  ToolRun r = run_on(bus, {"set-baud", "1", "3"});  // 500 000 baud
  EXPECT_EQ(r.code, kExitOk) << r.err;
  EXPECT_EQ(bus.servo(1).table[reg::kBaudRate], 3);
  EXPECT_NE(r.out.find("500000 baud"), std::string::npos);
  EXPECT_NE(r.out.find("--baud 500000 read 1"), std::string::npos);

  FakeServoBus bus2({1});
  r = run_on(bus2, {"set-baud", "1", "16"});  // 117 647 baud: termios'ta yok
  EXPECT_EQ(r.code, kExitUsage);
  EXPECT_EQ(bus2.servo(1).table[reg::kBaudRate], 1);
  EXPECT_TRUE(bus2.log().empty());  // hiçbir paket gönderilmedi

  r = run_on(bus2, {"set-baud", "8", "1"});
  EXPECT_EQ(r.code, kExitComm);
}

TEST(ServoTool, ReadPrintsControlTable) {
  FakeServoBus bus({2});
  auto& s = bus.servo(2);
  s.set_u16(reg::kPresentPosition, 600);
  s.set_u16(reg::kPresentLoad, 0x400 | 77);
  s.table[reg::kPresentVoltage] = 115;
  const ToolRun r = run_on(bus, {"read", "2"});
  EXPECT_EQ(r.code, kExitOk) << r.err;
  for (const char* line :
       {"id 2\n", "model 12\n", "baud_code 1 (1000000 baud)\n", "return_delay_us 500\n",
        "ccw_angle_limit 1023\n", "present_position 600\n", "present_load -77\n",
        "present_voltage_v 11.5\n", "present_temperature_c 30\n", "torque_enable 0\n"}) {
    EXPECT_NE(r.out.find(line), std::string::npos) << line << "\n" << r.out;
  }
  FakeServoBus empty(std::vector<int>{});
  const ToolRun e = run_on(empty, {"read", "2"});
  EXPECT_EQ(e.code, kExitComm);
  EXPECT_NE(e.err.find("ID 2 okunamadı: zaman aşımı"), std::string::npos);
}

TEST(ServoTool, TorqueOnOff) {
  FakeServoBus bus({3});
  ToolRun r = run_on(bus, {"torque", "3", "on"});
  EXPECT_EQ(r.code, kExitOk);
  EXPECT_EQ(bus.servo(3).table[reg::kTorqueEnable], 1);
  r = run_on(bus, {"torque", "3", "off"});
  EXPECT_EQ(r.code, kExitOk);
  EXPECT_EQ(bus.servo(3).table[reg::kTorqueEnable], 0);
  EXPECT_NE(r.out.find("tork kapalı"), std::string::npos);
  r = run_on(bus, {"torque", "4", "on"});
  EXPECT_EQ(r.code, kExitComm);
}

TEST(ServoTool, EchoOptionAndHelp) {
  FakeServoBus bus({1});
  bus.set_echo(true);
  EXPECT_EQ(run_on(bus, {"--echo", "read", "1"}).code, kExitOk);
  EXPECT_EQ(run_on(bus, {"read", "1"}).code, kExitComm);  // yankı durum paketi sanılır: hata
  const ToolRun h = run_on(bus, {"--help"});
  EXPECT_EQ(h.code, kExitOk);
  EXPECT_NE(h.out.find("Varsayılan aygıt: "), std::string::npos);
}

}  // namespace
}  // namespace delta_edge::servo_tool

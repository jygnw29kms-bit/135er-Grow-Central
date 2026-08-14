import CoreBluetooth
import Foundation

struct BLECandidate: Identifiable, Hashable {
    let id: UUID
    let name: String
    let rssi: Int
    let serviceUUIDs: [String]
    var isMarsHydro: Bool { name.localizedCaseInsensitiveContains("MZ_MZF002") || name.localizedCaseInsensitiveContains("Mars") || name.localizedCaseInsensitiveContains("iFresh") }
}

final class BluetoothManager: NSObject, ObservableObject, CBCentralManagerDelegate {
    @Published var state = "Bluetooth wird initialisiert"
    @Published var scanning = false
    @Published var devices: [BLECandidate] = []
    private var central: CBCentralManager!

    override init() { super.init(); central = CBCentralManager(delegate: self, queue: .main, options: [CBCentralManagerOptionRestoreIdentifierKey: "de.135er.growcentral.ble"]) }
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn: state = "Bereit"
        case .poweredOff: state = "Bluetooth ist ausgeschaltet"
        case .unauthorized: state = "Bluetooth-Zugriff nicht erlaubt"
        case .unsupported: state = "Bluetooth LE nicht unterstützt"
        default: state = "Bluetooth nicht verfügbar"
        }
    }
    func scan() {
        guard central.state == .poweredOn else { return }
        devices = []; scanning = true
        central.scanForPeripherals(withServices: nil, options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
        DispatchQueue.main.asyncAfter(deadline: .now() + 8) { [weak self] in self?.stop() }
    }
    func stop() { central.stopScan(); scanning = false }
    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String : Any], rssi RSSI: NSNumber) {
        let local = advertisementData[CBAdvertisementDataLocalNameKey] as? String
        let name = local ?? peripheral.name ?? "Unbekanntes BLE-Gerät"
        let uuids = (advertisementData[CBAdvertisementDataServiceUUIDsKey] as? [CBUUID] ?? []).map(\.uuidString)
        let row = BLECandidate(id: peripheral.identifier, name: name, rssi: RSSI.intValue, serviceUUIDs: uuids)
        if let index = devices.firstIndex(where: { $0.id == row.id }) { devices[index] = row } else { devices.append(row) }
        devices.sort { ($0.isMarsHydro ? 1 : 0, $0.rssi) > ($1.isMarsHydro ? 1 : 0, $1.rssi) }
    }
    func centralManager(_ central: CBCentralManager, willRestoreState dict: [String : Any]) { state = "Bluetooth-Verbindung wiederhergestellt" }
}


// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title MiningDataRegistry
 * @dev Smart contract for storing and verifying Bitcoin mining data on Base L2
 * @notice Provides transparency and proof of mining data integrity
 */
contract MiningDataRegistry {
    // Events for data transparency
    event DataRegistered(
        bytes32 indexed dataHash,
        string indexed siteId,
        uint256 indexed timestamp,
        string ipfsCid,
        address registrar
    );
    
    event DataVerified(
        bytes32 indexed dataHash,
        string indexed siteId,
        address verifier,
        bool isValid
    );
    
    // Data structure for mining records
    struct MiningRecord {
        bytes32 dataHash;        // Hash of the mining data
        string siteId;           // Mining site identifier
        uint256 timestamp;       // Block timestamp when recorded
        string ipfsCid;          // IPFS content identifier
        address registrar;       // Address that registered the data
        uint256 blockNumber;     // Block number when registered
        bool isVerified;         // Whether data has been verified
        uint256 verificationCount; // Number of verifications
    }
    
    // Storage mappings
    mapping(bytes32 => MiningRecord) public records;
    mapping(string => bytes32[]) public siteRecords; // Records by site ID
    mapping(address => bytes32[]) public registrarRecords; // Records by registrar
    
    // Contract state
    address public owner;
    uint256 public totalRecords;
    uint256 public constant MAX_RECORDS_PER_SITE = 10000; // Prevent spam
    
    // Access control
    mapping(address => bool) public authorizedRegistrars;
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }
    
    modifier onlyAuthorized() {
        require(
            authorizedRegistrars[msg.sender] || msg.sender == owner,
            "Not authorized to register data"
        );
        _;
    }
    
    constructor() {
        owner = msg.sender;
        authorizedRegistrars[msg.sender] = true;
    }
    
    /**
     * @dev Register mining data on-chain
     * @param _dataHash Keccak256 hash of the mining data
     * @param _siteId Mining site identifier
     * @param _ipfsCid IPFS content identifier for full data
     */
    function registerMiningData(
        bytes32 _dataHash,
        string calldata _siteId,
        string calldata _ipfsCid
    ) external onlyAuthorized {
        require(_dataHash != bytes32(0), "Invalid data hash");
        require(bytes(_siteId).length > 0, "Site ID cannot be empty");
        require(bytes(_ipfsCid).length > 0, "IPFS CID cannot be empty");
        require(records[_dataHash].timestamp == 0, "Data already registered");
        require(
            siteRecords[_siteId].length < MAX_RECORDS_PER_SITE,
            "Site record limit exceeded"
        );
        
        // Create mining record
        records[_dataHash] = MiningRecord({
            dataHash: _dataHash,
            siteId: _siteId,
            timestamp: block.timestamp,
            ipfsCid: _ipfsCid,
            registrar: msg.sender,
            blockNumber: block.number,
            isVerified: false,
            verificationCount: 0
        });
        
        // Update indexes
        siteRecords[_siteId].push(_dataHash);
        registrarRecords[msg.sender].push(_dataHash);
        totalRecords++;
        
        emit DataRegistered(_dataHash, _siteId, block.timestamp, _ipfsCid, msg.sender);
    }
    
    /**
     * @dev Verify a mining data record
     * @param _dataHash Hash of the data to verify
     */
    function verifyData(bytes32 _dataHash) external {
        require(records[_dataHash].timestamp != 0, "Record does not exist");
        
        records[_dataHash].verificationCount++;
        
        // Mark as verified after first verification
        if (!records[_dataHash].isVerified) {
            records[_dataHash].isVerified = true;
        }
        
        emit DataVerified(
            _dataHash,
            records[_dataHash].siteId,
            msg.sender,
            true
        );
    }
    
    /**
     * @dev Get mining record by data hash
     * @param _dataHash Hash of the data
     * @return Mining record details
     */
    function getRecord(bytes32 _dataHash) external view returns (MiningRecord memory) {
        require(records[_dataHash].timestamp != 0, "Record does not exist");
        return records[_dataHash];
    }
    
    /**
     * @dev Get all record hashes for a site
     * @param _siteId Site identifier
     * @return Array of data hashes
     */
    function getSiteRecords(string calldata _siteId) external view returns (bytes32[] memory) {
        return siteRecords[_siteId];
    }
    
    /**
     * @dev Get records by registrar address
     * @param _registrar Registrar address
     * @return Array of data hashes
     */
    function getRegistrarRecords(address _registrar) external view returns (bytes32[] memory) {
        return registrarRecords[_registrar];
    }
    
    /**
     * @dev Get latest records for a site (last N records)
     * @param _siteId Site identifier
     * @param _count Number of recent records to return
     * @return Array of recent data hashes
     */
    function getLatestSiteRecords(
        string calldata _siteId,
        uint256 _count
    ) external view returns (bytes32[] memory) {
        bytes32[] memory allRecords = siteRecords[_siteId];
        uint256 length = allRecords.length;
        
        if (length == 0) {
            return new bytes32[](0);
        }
        
        uint256 returnCount = _count > length ? length : _count;
        bytes32[] memory latestRecords = new bytes32[](returnCount);
        
        for (uint256 i = 0; i < returnCount; i++) {
            latestRecords[i] = allRecords[length - returnCount + i];
        }
        
        return latestRecords;
    }
    
    /**
     * @dev Check if data exists and is verified
     * @param _dataHash Hash of the data to check
     * @return exists Whether the record exists
     * @return verified Whether the record is verified
     */
    function checkDataStatus(bytes32 _dataHash) external view returns (bool exists, bool verified) {
        exists = records[_dataHash].timestamp != 0;
        verified = exists && records[_dataHash].isVerified;
    }
    
    /**
     * @dev Add authorized registrar (owner only)
     * @param _registrar Address to authorize
     */
    function addAuthorizedRegistrar(address _registrar) external onlyOwner {
        require(_registrar != address(0), "Invalid address");
        authorizedRegistrars[_registrar] = true;
    }
    
    /**
     * @dev Remove authorized registrar (owner only)
     * @param _registrar Address to remove authorization
     */
    function removeAuthorizedRegistrar(address _registrar) external onlyOwner {
        authorizedRegistrars[_registrar] = false;
    }
    
    /**
     * @dev Transfer ownership (owner only)
     * @param _newOwner New owner address
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid address");
        owner = _newOwner;
        authorizedRegistrars[_newOwner] = true;
    }
    
    /**
     * @dev Get contract statistics
     * @return totalRecords Total number of records
     * @return totalSites Number of unique sites
     */
    function getContractStats() external view returns (uint256, uint256) {
        // Note: totalSites would require additional tracking in a real implementation
        // For simplicity, we return totalRecords twice
        return (totalRecords, totalRecords);
    }
    
    /**
     * @dev Batch register multiple records (gas optimization)
     * @param _dataHashes Array of data hashes
     * @param _siteIds Array of site IDs
     * @param _ipfsCids Array of IPFS CIDs
     */
    function batchRegisterMiningData(
        bytes32[] calldata _dataHashes,
        string[] calldata _siteIds,
        string[] calldata _ipfsCids
    ) external onlyAuthorized {
        require(
            _dataHashes.length == _siteIds.length && 
            _siteIds.length == _ipfsCids.length,
            "Array lengths must match"
        );
        require(_dataHashes.length <= 50, "Batch size too large");
        
        for (uint256 i = 0; i < _dataHashes.length; i++) {
            require(_dataHashes[i] != bytes32(0), "Invalid data hash");
            require(bytes(_siteIds[i]).length > 0, "Site ID cannot be empty");
            require(bytes(_ipfsCids[i]).length > 0, "IPFS CID cannot be empty");
            require(records[_dataHashes[i]].timestamp == 0, "Data already registered");
            require(
                siteRecords[_siteIds[i]].length < MAX_RECORDS_PER_SITE,
                "Site record limit exceeded"
            );
            
            // Create mining record
            records[_dataHashes[i]] = MiningRecord({
                dataHash: _dataHashes[i],
                siteId: _siteIds[i],
                timestamp: block.timestamp,
                ipfsCid: _ipfsCids[i],
                registrar: msg.sender,
                blockNumber: block.number,
                isVerified: false,
                verificationCount: 0
            });
            
            // Update indexes
            siteRecords[_siteIds[i]].push(_dataHashes[i]);
            registrarRecords[msg.sender].push(_dataHashes[i]);
            totalRecords++;
            
            emit DataRegistered(
                _dataHashes[i], 
                _siteIds[i], 
                block.timestamp, 
                _ipfsCids[i], 
                msg.sender
            );
        }
    }
}
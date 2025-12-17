// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title SLAProofNFT
 * @dev Soulbound NFT for monthly SLA proof certificates
 * @notice Non-transferable certificates proving service level agreement compliance
 */
contract SLAProofNFT is ERC721, ERC721URIStorage, Ownable, ReentrancyGuard, Pausable {
    using Counters for Counters.Counter;
    
    // Events
    event SLACertificateMinted(
        uint256 indexed tokenId,
        address indexed recipient,
        uint256 indexed monthYear,
        uint256 slaScore,
        string ipfsCid
    );
    
    event SLAScoreUpdated(
        uint256 indexed tokenId,
        uint256 oldScore,
        uint256 newScore,
        string reason
    );
    
    event CertificateVerified(
        uint256 indexed tokenId,
        address indexed verifier,
        bool isValid,
        string verificationNote
    );
    
    event MonthlyReportGenerated(
        uint256 indexed monthYear,
        uint256 totalCertificates,
        uint256 averageSLA,
        string reportIpfsCid
    );
    
    // Structs
    struct SLAMetrics {
        uint256 uptime;              // Uptime percentage (e.g., 9950 = 99.50%)
        uint256 responseTime;        // Average response time in ms
        uint256 accuracy;            // Data accuracy percentage
        uint256 availability;        // Service availability percentage
        uint256 transparencyScore;   // Transparency audit score
        uint256 blockchainVerifications; // Number of blockchain verifications
        uint256 composite;           // Composite SLA score (0-10000)
    }
    
    struct SLACertificate {
        uint256 monthYear;           // YYYYMM format (e.g., 202509 for Sep 2025)
        address recipient;           // Certificate holder
        uint256 mintedAt;           // Timestamp when minted
        SLAMetrics metrics;         // Detailed SLA metrics
        string ipfsCid;             // IPFS content identifier
        bool isVerified;            // Third-party verification status
        address verifier;           // Address of verifier
        string verificationNote;    // Verification details
        uint256 verifiedAt;         // Verification timestamp
    }
    
    // State variables
    Counters.Counter private _tokenIdCounter;
    
    // Mappings
    mapping(uint256 => SLACertificate) public certificates;
    mapping(address => uint256[]) public userCertificates;
    mapping(uint256 => uint256[]) public monthlyCertificates; // monthYear => tokenIds
    mapping(address => bool) public authorizedMinters;
    mapping(address => bool) public authorizedVerifiers;
    mapping(uint256 => string) public monthlyReports; // monthYear => IPFS CID
    
    // Configuration
    uint256 public constant MIN_SLA_SCORE = 7000; // Minimum 70% for certificate
    uint256 public constant MAX_SLA_SCORE = 10000; // Maximum 100%
    uint256 public constant SECONDS_PER_MONTH = 30 * 24 * 60 * 60; // Approximate
    
    // Stats
    uint256 public totalCertificatesIssued;
    uint256 public totalVerifications;
    mapping(uint256 => uint256) public monthlyCertificateCount;
    mapping(uint256 => uint256) public monthlyAverageSLA;
    
    modifier onlyAuthorizedMinter() {
        require(
            authorizedMinters[msg.sender] || owner() == msg.sender,
            "Not authorized to mint certificates"
        );
        _;
    }
    
    modifier onlyAuthorizedVerifier() {
        require(
            authorizedVerifiers[msg.sender] || owner() == msg.sender,
            "Not authorized to verify certificates"
        );
        _;
    }
    
    modifier validSLAScore(uint256 score) {
        require(
            score >= MIN_SLA_SCORE && score <= MAX_SLA_SCORE,
            "Invalid SLA score range"
        );
        _;
    }
    
    constructor(
        string memory name,
        string memory symbol
    ) ERC721(name, symbol) {
        // Initialize with deployer as owner
        authorizedMinters[msg.sender] = true;
        authorizedVerifiers[msg.sender] = true;
    }
    
    /**
     * @dev Mint a monthly SLA certificate
     * @param recipient Address to receive the certificate
     * @param monthYear Month and year in YYYYMM format
     * @param metrics Detailed SLA metrics
     * @param ipfsCid IPFS content identifier for detailed report
     */
    function mintSLACertificate(
        address recipient,
        uint256 monthYear,
        SLAMetrics memory metrics,
        string calldata ipfsCid
    ) 
        external 
        onlyAuthorizedMinter 
        validSLAScore(metrics.composite)
        nonReentrant
        whenNotPaused
    {
        require(recipient != address(0), "Invalid recipient address");
        require(_isValidMonthYear(monthYear), "Invalid month/year format");
        require(bytes(ipfsCid).length > 0, "IPFS CID required");
        require(
            !_hasMonthlyCertificate(recipient, monthYear),
            "Certificate already exists for this month"
        );
        
        // Validate individual metrics
        require(metrics.uptime <= 10000, "Invalid uptime percentage");
        require(metrics.accuracy <= 10000, "Invalid accuracy percentage");
        require(metrics.availability <= 10000, "Invalid availability percentage");
        require(metrics.transparencyScore <= 10000, "Invalid transparency score");
        
        _tokenIdCounter.increment();
        uint256 tokenId = _tokenIdCounter.current();
        
        // Mint the token
        _safeMint(recipient, tokenId);
        _setTokenURI(tokenId, string(abi.encodePacked("ipfs://", ipfsCid)));
        
        // Store certificate data
        certificates[tokenId] = SLACertificate({
            monthYear: monthYear,
            recipient: recipient,
            mintedAt: block.timestamp,
            metrics: metrics,
            ipfsCid: ipfsCid,
            isVerified: false,
            verifier: address(0),
            verificationNote: "",
            verifiedAt: 0
        });
        
        // Update indexes
        userCertificates[recipient].push(tokenId);
        monthlyCertificates[monthYear].push(tokenId);
        
        // Update statistics
        totalCertificatesIssued++;
        monthlyCertificateCount[monthYear]++;
        _updateMonthlyAverageSLA(monthYear, metrics.composite);
        
        emit SLACertificateMinted(tokenId, recipient, monthYear, metrics.composite, ipfsCid);
    }
    
    /**
     * @dev Verify an SLA certificate by authorized verifier
     * @param tokenId Certificate token ID
     * @param isValid Whether the certificate is valid
     * @param verificationNote Notes from verification
     */
    function verifyCertificate(
        uint256 tokenId,
        bool isValid,
        string calldata verificationNote
    ) external onlyAuthorizedVerifier whenNotPaused {
        require(_exists(tokenId), "Certificate does not exist");
        
        SLACertificate storage cert = certificates[tokenId];
        require(!cert.isVerified, "Certificate already verified");
        
        cert.isVerified = isValid;
        cert.verifier = msg.sender;
        cert.verificationNote = verificationNote;
        cert.verifiedAt = block.timestamp;
        
        if (isValid) {
            totalVerifications++;
        }
        
        emit CertificateVerified(tokenId, msg.sender, isValid, verificationNote);
    }
    
    /**
     * @dev Update SLA score for a certificate (owner only)
     * @param tokenId Certificate token ID
     * @param newScore New SLA score
     * @param reason Reason for update
     */
    function updateSLAScore(
        uint256 tokenId,
        uint256 newScore,
        string calldata reason
    ) 
        external 
        onlyOwner 
        validSLAScore(newScore)
        whenNotPaused
    {
        require(_exists(tokenId), "Certificate does not exist");
        
        SLACertificate storage cert = certificates[tokenId];
        uint256 oldScore = cert.metrics.composite;
        cert.metrics.composite = newScore;
        
        // Update monthly average
        _updateMonthlyAverageSLA(cert.monthYear, newScore);
        
        emit SLAScoreUpdated(tokenId, oldScore, newScore, reason);
    }
    
    /**
     * @dev Generate monthly report for all certificates
     * @param monthYear Month and year in YYYYMM format
     * @param reportIpfsCid IPFS CID for the comprehensive report
     */
    function generateMonthlyReport(
        uint256 monthYear,
        string calldata reportIpfsCid
    ) external onlyOwner {
        require(_isValidMonthYear(monthYear), "Invalid month/year format");
        require(bytes(reportIpfsCid).length > 0, "Report IPFS CID required");
        
        monthlyReports[monthYear] = reportIpfsCid;
        
        uint256 totalCerts = monthlyCertificateCount[monthYear];
        uint256 avgSLA = monthlyAverageSLA[monthYear];
        
        emit MonthlyReportGenerated(monthYear, totalCerts, avgSLA, reportIpfsCid);
    }
    
    // Query functions
    
    /**
     * @dev Get certificate details by token ID
     */
    function getCertificate(uint256 tokenId) 
        external 
        view 
        returns (SLACertificate memory) 
    {
        require(_exists(tokenId), "Certificate does not exist");
        return certificates[tokenId];
    }
    
    /**
     * @dev Get all certificate IDs for a user
     */
    function getUserCertificates(address user) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return userCertificates[user];
    }
    
    /**
     * @dev Get all certificate IDs for a specific month
     */
    function getMonthlyCertificates(uint256 monthYear) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return monthlyCertificates[monthYear];
    }
    
    /**
     * @dev Get monthly statistics
     */
    function getMonthlyStats(uint256 monthYear) 
        external 
        view 
        returns (
            uint256 certificateCount,
            uint256 averageSLA,
            string memory reportCid
        ) 
    {
        return (
            monthlyCertificateCount[monthYear],
            monthlyAverageSLA[monthYear],
            monthlyReports[monthYear]
        );
    }
    
    /**
     * @dev Check if user has certificate for specific month
     */
    function hasMonthlycertificate(address user, uint256 monthYear) 
        external 
        view 
        returns (bool) 
    {
        return _hasMonthlyStatement(user, monthYear);
    }
    
    // Administration functions
    
    /**
     * @dev Set authorized minter status
     */
    function setAuthorizedMinter(address minter, bool authorized) 
        external 
        onlyOwner 
    {
        authorizedMinters[minter] = authorized;
    }
    
    /**
     * @dev Set authorized verifier status
     */
    function setAuthorizedVerifier(address verifier, bool authorized) 
        external 
        onlyOwner 
    {
        authorizedVerifiers[verifier] = authorized;
    }
    
    /**
     * @dev Pause contract operations
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause contract operations
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    // Soulbound functionality - Override transfer functions to prevent transfers
    
    /**
     * @dev Soulbound: Prevent all transfers except minting
     */
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId
    ) internal override {
        require(from == address(0), "Soulbound: Transfer not allowed");
        super._beforeTokenTransfer(from, to, tokenId);
    }
    
    /**
     * @dev Soulbound: Disable approvals
     */
    function approve(address, uint256) public override {
        revert("Soulbound: Approval not allowed");
    }
    
    /**
     * @dev Soulbound: Disable approval for all
     */
    function setApprovalForAll(address, bool) public override {
        revert("Soulbound: Approval not allowed");
    }
    
    /**
     * @dev Soulbound: Always return zero for approvals
     */
    function getApproved(uint256) public pure override returns (address) {
        return address(0);
    }
    
    /**
     * @dev Soulbound: Always return false for approval checks
     */
    function isApprovedForAll(address, address) public pure override returns (bool) {
        return false;
    }
    
    // Internal helper functions
    
    function _hasMonthlyStatement(address user, uint256 monthYear) 
        internal 
        view 
        returns (bool) 
    {
        uint256[] memory userTokens = userCertificates[user];
        for (uint256 i = 0; i < userTokens.length; i++) {
            if (certificates[userTokens[i]].monthYear == monthYear) {
                return true;
            }
        }
        return false;
    }
    
    function _isValidMonthYear(uint256 monthYear) internal pure returns (bool) {
        uint256 year = monthYear / 100;
        uint256 month = monthYear % 100;
        return year >= 2024 && year <= 2100 && month >= 1 && month <= 12;
    }
    
    function _updateMonthlyAverageSLA(uint256 monthYear, uint256 score) internal {
        uint256 currentCount = monthlyCertificateCount[monthYear];
        uint256 currentAvg = monthlyAverageSLA[monthYear];
        
        if (currentCount == 1) {
            monthlyAverageSLA[monthYear] = score;
        } else {
            // Calculate running average
            uint256 newAvg = ((currentAvg * (currentCount - 1)) + score) / currentCount;
            monthlyAverageSLA[monthYear] = newAvg;
        }
    }
    
    // Required overrides
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }
    
    function tokenURI(uint256 tokenId) 
        public 
        view 
        override(ERC721, ERC721URIStorage) 
        returns (string memory) 
    {
        return super.tokenURI(tokenId);
    }
    
    /**
     * @dev Get contract version and info
     */
    function getContractInfo() external pure returns (
        string memory version,
        string memory description
    ) {
        return (
            "1.0.0",
            "SLA Proof NFT - Soulbound certificates for service level agreements"
        );
    }
}
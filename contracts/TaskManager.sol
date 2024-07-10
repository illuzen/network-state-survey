// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import "./IERC20.sol";
import "./IERC721.sol";

contract TaskManager {
    enum RewardType {
        CASH,
        CRYPTO,
        COLLECTIBLE
    }

    struct Task {
        uint id;
        address owner;
        RewardType rewardType;
        address token;
        uint rewardSize;
        uint numRewards;
        uint deadline;
        uint rewardsPaid;
        uint maxRegistered;
        uint numRegistered;
        bytes32 descriptionHash;
    }

    struct Submission {
        uint taskId;
        address submitter;
        string link; // bytes32 for ipfs hash?
    }

    mapping (uint => Task) public taskMap;
    mapping (address => mapping (uint => Submission)) public submissionMap; // (submitter, taskId) -> Submission
    mapping (address => bool) public whitelistedTokens;
    address public manager;
    uint public numTasks;

    event TaskCreated(address indexed owner, RewardType indexed rewardType, uint taskId, bytes32 descriptionHash);
    event TaskExpired(uint indexed taskId);
    event Registration(address indexed registree, uint indexed taskId);
    event SubmissionCreated(address indexed submitter, uint indexed taskId, string link);
    event SubmissionAccepted(address indexed submitter, uint indexed taskId, string link);

    constructor(address _manager) {
        manager = _manager;
    }

    function whitelistToken (address token, bool whitelisted) public {
        require(msg.sender == manager, 'Must be manager to edit whitelist');
        whitelistedTokens[token] = whitelisted;
    }

    function createTask (RewardType rewardType, address token, uint rewardSize, uint numRewards, uint deadline, uint maxRegistered, bytes32 descriptionHash) public payable {
//        require(msg.sender == owner || msg.sender == manager, 'Must be manager to create task for others');
        require(whitelistedTokens[token] == true || token == address(0), 'Token must be whitelisted');
        if (rewardType == RewardType.CASH) {
            // sending tokens
            IERC20 erc20 = IERC20(token);
            uint depositAmount = rewardSize * numRewards;
            require(erc20.allowance(msg.sender, address(this)) >= depositAmount, 'Insufficient allowance');
            require(erc20.transferFrom(msg.sender, address(this), depositAmount), 'Transfer failed');
        } else if (rewardType == RewardType.CRYPTO) {
            // sending eth
            require(msg.value == rewardSize * numRewards, 'Insufficient ETH sent');
            require(token == address(0), 'Non-zero token address paired with eth payment');
        } else if (rewardType == RewardType.COLLECTIBLE) {
            require(rewardSize == 1, 'Can only send one nft per task reward');
            IERC721 erc721 = IERC721(token);
            // this should be minter
        }

        numTasks += 1;
        Task storage task = taskMap[numTasks];
        task.id = numTasks;
        task.owner = msg.sender;
        task.rewardType = rewardType;
        task.token = token;
        task.rewardSize = rewardSize;
        task.numRewards = numRewards;
        task.deadline = deadline;
        task.rewardsPaid = 0;
        task.maxRegistered = maxRegistered;
        task.numRegistered = 0;
        task.descriptionHash = descriptionHash;
        emit TaskCreated(task.owner, rewardType, task.id, descriptionHash);
    }

    function registerForTask (address registree, uint taskId) public {
        require(msg.sender == registree || msg.sender == manager, 'Must be manager to register for others');
        Task storage task = taskMap[taskId];
        require(task.id == taskId, 'Invalid task id');
        require(task.deadline > block.timestamp, 'Expired task');
        require(task.maxRegistered > task.numRegistered, 'Maximum already registered');
        task.numRegistered += 1;
        emit Registration(registree, taskId);
    }

    function submitTask (address submitter, uint taskId, string calldata link) public {
        require(msg.sender == submitter || msg.sender == manager, 'Must be manager to submit tasks for others');
        Submission storage submission = submissionMap[submitter][taskId];
        submission.submitter = submitter;
        submission.taskId = taskId;
        submission.link = link;
        emit SubmissionCreated(submitter, taskId, link);
    }

    function acceptSubmission (address payable submitter, uint taskId) public {
        Task storage task = taskMap[taskId];
        require(msg.sender == task.owner, 'Only owner can accept submissions');
        require(task.rewardsPaid < task.numRewards * task.rewardSize, 'Max rewards already reached');
        Submission storage submission = submissionMap[submitter][taskId];
        if (task.rewardType == RewardType.CASH) {
            // token
            IERC20 erc20 = IERC20(task.token);
            erc20.transfer(submitter, task.rewardSize);
        } else if (task.rewardType == RewardType.CRYPTO) {
            // eth
            submitter.transfer(task.rewardSize);
        } else if (task.rewardType == RewardType.COLLECTIBLE) {
            IERC721 erc721 = IERC721(task.token);
            erc721.mint(submitter);
        }

        task.rewardsPaid += task.rewardSize;
        emit SubmissionAccepted(submitter, taskId, submission.link);
    }

    function expireTask (uint taskId) public {
        Task storage task = taskMap[taskId];
        require(msg.sender == task.owner, 'Only owner can expire task');
        require(block.timestamp > task.deadline, 'Task deadline has not passed');
        uint remainingUnpaid = (task.numRewards * task.rewardSize) - task.rewardsPaid;
        if (task.rewardType == RewardType.CASH) {
            // token
            IERC20 erc20 = IERC20(task.token);
            // TODO: make this safe for weird tokens? or just don't whitelist weird tokens
            erc20.transfer(task.owner, remainingUnpaid);
        } else if (task.rewardType == RewardType.CRYPTO) {
            // eth
            payable(task.owner).transfer(remainingUnpaid);
        } else if (task.rewardType == RewardType.COLLECTIBLE) {
            // don't mint
        }

        task.rewardsPaid += remainingUnpaid;
        emit TaskExpired(taskId);
    }

}

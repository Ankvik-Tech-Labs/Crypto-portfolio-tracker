"""Chain scanner for discovering user positions via event logs."""

from typing import Any

from crypto_portfolio_tracker.core.models import ChainActivity
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.data import get_all_supported_chains


class ChainScanner:
    """
    Scans chains for user activity and protocol positions using event logs.

    Uses eth_getLogs to efficiently detect which protocols a user has
    interacted with, avoiding expensive contract calls for inactive protocols.

    Parameters
    ----------
    rpc_provider : Any
        RPC provider instance for making queries
    debug : bool
        Enable debug output (default: False)

    """

    def __init__(self, rpc_provider: Any, debug: bool = False) -> None:
        self.rpc_provider = rpc_provider
        self.debug = debug

    def detect_active_chains(self, user_address: str) -> list[str]:
        """
        Detect which chains the user has activity on.

        Parameters
        ----------
        user_address : str
            User wallet address

        Returns
        -------
        list[str]
            List of chain names with detected activity

        """
        active_chains = []
        supported_chains = get_all_supported_chains()

        for chain in supported_chains:
            if self._has_chain_activity(user_address, chain):
                active_chains.append(chain)

        return active_chains

    def _has_chain_activity(self, user_address: str, chain: str) -> bool:
        """
        Check if user has any activity on a chain.

        Uses a quick Transfer event query to detect token movements.

        Parameters
        ----------
        user_address : str
            User address
        chain : str
            Chain name

        Returns
        -------
        bool
            True if activity detected

        """
        try:
            if self.debug:
                pass

            # Query for Transfer events involving user address
            # Transfer event signature: Transfer(address,address,uint256)
            topics = [
                "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",  # Transfer
                None,  # from (any)
                self._pad_address(user_address),  # to (user)
            ]

            if self.debug:
                pass

            logs = self.rpc_provider.make_request(
                "eth_getLogs",
                [
                    {
                        "fromBlock": "0x0",
                        "toBlock": "latest",
                        "topics": topics,
                    }
                ],
            )

            has_activity = len(logs) > 0
            if self.debug:
                pass

            return has_activity
        except Exception:
            # If query fails, assume no activity to avoid false positives
            if self.debug:
                pass
            return False

    def discover_protocols(self, user_address: str, chain: str) -> list[str]:
        """
        Discover which protocols user has positions on via event logs.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name

        Returns
        -------
        list[str]
            List of protocol names with detected positions

        """
        if self.debug:
            pass

        discovered_protocols = []
        discovery_events = ProtocolRegistry.get_discovery_events(chain)

        if self.debug:
            pass

        for protocol_name, event_signatures in discovery_events.items():
            if self.debug:
                pass

            if self._has_protocol_activity(user_address, chain, event_signatures):
                discovered_protocols.append(protocol_name)
                if self.debug:
                    pass
            elif self.debug:
                pass

        if self.debug:
            pass

        return discovered_protocols

    def _has_protocol_activity(
        self,
        user_address: str,
        chain: str,
        event_signatures: list[str],
    ) -> bool:
        """
        Check if user has activity with specific event signatures.

        Parameters
        ----------
        user_address : str
            User address
        chain : str
            Chain name
        event_signatures : list[str]
            Event signature hashes to query

        Returns
        -------
        bool
            True if any matching events found

        """
        try:
            padded_address = self._pad_address(user_address)

            for event_sig in event_signatures:
                if self.debug:
                    pass

                # Query logs with event signature and user address
                # Try user address in different topic positions (indexed params vary by event)
                for topics in [
                    [event_sig, padded_address],  # User as first indexed param
                    [event_sig, None, padded_address],  # User as second indexed param
                    [event_sig, None, None, padded_address],  # User as third indexed param
                ]:
                    try:
                        logs = self._query_logs_with_chunking(
                            topics=topics,
                            from_block="0x0",
                            to_block="latest",
                        )

                        if self.debug:
                            pass

                        if len(logs) > 0:
                            if self.debug:
                                pass
                            return True

                    except Exception:
                        if self.debug:
                            pass
                        continue

            return False
        except Exception:
            # If query fails, assume no activity
            if self.debug:
                pass
            return False

    def _query_logs_with_chunking(
        self,
        topics: list,
        from_block: str,
        to_block: str,
    ) -> list:
        """
        Query logs with automatic block range chunking on large result errors.

        Parameters
        ----------
        topics : list
            Event topic filters
        from_block : str
            Starting block (hex)
        to_block : str
            Ending block (hex or 'latest')

        Returns
        -------
        list
            Combined logs from all chunks

        """
        try:
            logs = self.rpc_provider.make_request(
                "eth_getLogs",
                [
                    {
                        "fromBlock": from_block,
                        "toBlock": to_block,
                        "topics": topics,
                    }
                ],
            )
            return logs

        except Exception as e:
            error_msg = str(e)

            # Check if error is about too many results with suggested block ranges
            if "query returned more than 10000 results" in error_msg or "Try with this block range" in error_msg:
                # Extract suggested block range from error message
                # Format: "Try with this block range [0xE4E58A, 0xFEE64F]"
                import re

                match = re.search(r"\[0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+)\]", error_msg)
                if match:
                    suggested_from = f"0x{match.group(1)}"
                    suggested_to = f"0x{match.group(2)}"

                    if self.debug:
                        pass

                    # Query the suggested range
                    chunk_logs = self._query_logs_with_chunking(topics, suggested_from, suggested_to)

                    # Also query before and after the suggested range (if there's more data)
                    all_logs = chunk_logs

                    # Query before suggested range (from original start to suggested start)
                    if from_block != suggested_from:
                        try:
                            # Calculate block before suggested start
                            suggested_from_int = int(suggested_from, 16)
                            before_end = hex(suggested_from_int - 1)
                            before_logs = self._query_logs_with_chunking(topics, from_block, before_end)
                            all_logs.extend(before_logs)
                        except Exception:
                            pass

                    # Query after suggested range (from suggested end to original end)
                    if to_block == "latest" or (to_block != suggested_to):
                        try:
                            # Calculate block after suggested end
                            suggested_to_int = int(suggested_to, 16)
                            after_start = hex(suggested_to_int + 1)
                            after_logs = self._query_logs_with_chunking(topics, after_start, to_block)
                            all_logs.extend(after_logs)
                        except Exception:
                            pass

                    return all_logs

            # Re-raise if not a "too many results" error or can't parse block range
            raise

    def scan_chain(self, user_address: str, chain: str) -> ChainActivity:
        """
        Perform complete chain scan for a user.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name

        Returns
        -------
        ChainActivity
            Activity summary including detected protocols

        """
        has_activity = self._has_chain_activity(user_address, chain)

        if not has_activity:
            return ChainActivity(
                chain=chain,
                has_activity=False,
                protocols_detected=[],
            )

        protocols = self.discover_protocols(user_address, chain)

        return ChainActivity(
            chain=chain,
            has_activity=True,
            protocols_detected=protocols,
        )

    def scan_all_chains(self, user_address: str) -> list[ChainActivity]:
        """
        Scan all supported chains for user activity.

        Parameters
        ----------
        user_address : str
            User wallet address

        Returns
        -------
        list[ChainActivity]
            Activity summary for each chain

        """
        results = []
        active_chains = self.detect_active_chains(user_address)

        for chain in get_all_supported_chains():
            if chain in active_chains:
                activity = self.scan_chain(user_address, chain)
                results.append(activity)
            else:
                # Skip full scan for inactive chains
                results.append(
                    ChainActivity(
                        chain=chain,
                        has_activity=False,
                        protocols_detected=[],
                    )
                )

        return results

    @staticmethod
    def _pad_address(address: str) -> str:
        """
        Pad address to 32 bytes for topic filtering.

        Parameters
        ----------
        address : str
            Ethereum address (0x prefixed)

        Returns
        -------
        str
            Padded address for use in topics

        """
        # Remove 0x prefix, pad to 64 hex chars, re-add 0x
        clean_addr = address.lower().replace("0x", "")
        return "0x" + clean_addr.zfill(64)

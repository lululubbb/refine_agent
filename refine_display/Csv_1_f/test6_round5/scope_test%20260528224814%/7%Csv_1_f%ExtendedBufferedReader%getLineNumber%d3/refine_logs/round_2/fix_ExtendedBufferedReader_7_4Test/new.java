package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.StringReader;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ExtendedBufferedReader_7_4Test {
    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        extendedBufferedReader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
    }

    @Test
    void testGetLineNumber_initialValue() throws Exception {
        // Assert the expected line number
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingLines() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line

        // Assert the expected line number
        assertEquals(2, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterMultipleReads() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line
        extendedBufferedReader.readLine(); // Read third line

        // Assert the expected line number
        assertEquals(3, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingNoLines() throws Exception {
        // Assert the expected line number
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_boundaryAfterReadingLastLine() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line
        extendedBufferedReader.readLine(); // Read third line
        extendedBufferedReader.readLine(); // Read beyond the last line

        // Assert the expected line number after reading beyond the last line
        assertEquals(3, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReset() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line

        // Reset the reader
        extendedBufferedReader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        // Assert the expected line number after reset
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_emptyReader() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        // Assert the expected line number for an empty reader
        assertEquals(0, emptyReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingEmptyReader() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        emptyReader.readLine(); // Attempt to read from empty reader
        // Assert the expected line number after reading from an empty reader
        assertEquals(0, emptyReader.getLineNumber());
    }
}
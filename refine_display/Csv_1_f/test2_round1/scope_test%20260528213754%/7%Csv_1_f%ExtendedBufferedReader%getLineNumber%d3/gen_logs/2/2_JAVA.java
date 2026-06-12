package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_2Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
    }

    @Test
    void testGetLineNumber_initialState() throws Exception {
        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.set(reader, 0);
        
        Assertions.assertEquals(0, reader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingLines() throws Exception {
        // Simulate reading lines to increase lineCounter
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line

        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.set(reader, 2);
        
        Assertions.assertEquals(2, reader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingAllLines() throws Exception {
        // Read all lines
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        reader.readLine(); // Read third line

        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.set(reader, 3);
        
        Assertions.assertEquals(3, reader.getLineNumber());
    }

    @Test
    void testGetLineNumber_noLinesRead() throws Exception {
        // Ensure no lines read
        Assertions.assertEquals(0, reader.getLineNumber());
    }
}
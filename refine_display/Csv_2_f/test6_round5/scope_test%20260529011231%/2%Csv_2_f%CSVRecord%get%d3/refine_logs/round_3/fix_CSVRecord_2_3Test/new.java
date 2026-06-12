package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_2_3Test {
    private CSVRecord csvRecord;

    @BeforeEach
    public void setUp() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        mapping.put("key3", 2);
        csvRecord = new CSVRecord(values, mapping, "comment", 1);
    }

    @Test
    public void testget_validIndex() throws Exception {
        assertEquals("value1", csvRecord.get(0));
        assertEquals("value2", csvRecord.get(1));
        assertEquals("value3", csvRecord.get(2));
    }

    @Test
    public void testget_invalidIndex() throws Exception {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(-1));
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(3));
    }

    @Test
    public void testget_emptyArray() throws Exception {
        CSVRecord emptyRecord = new CSVRecord(new String[0], new HashMap<>(), null, 0);
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> emptyRecord.get(0));
    }

    @Test
    public void testget_boundaryValues() throws Exception {
        String[] boundaryValues = {null, "", "value1", "value2", "value3"};
        CSVRecord boundaryRecord = new CSVRecord(boundaryValues, new HashMap<>(), null, 0);
        
        assertEquals(null, boundaryRecord.get(0));
        assertEquals("", boundaryRecord.get(1));
        assertEquals("value1", boundaryRecord.get(2));
        assertEquals("value2", boundaryRecord.get(3));
        assertEquals("value3", boundaryRecord.get(4));
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> boundaryRecord.get(5)); // Test out of bounds
    }
}
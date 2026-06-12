package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_4Test {

    @Test
    public void testGet_validIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.get(1);
        
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(3);
        });
    }

    @Test
    public void testGet_negativeIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(-1);
        });
    }

    @Test
    public void testGet_emptyValuesArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(0);
        });
    }

    @Test
    public void testGet_boundaryValues() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testGet_nullValue() throws Exception {
        String[] values = {"value1", null, "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertEquals(null, record.get(1));
    }

    @Test
    public void testGet_emptyString() throws Exception {
        String[] values = {"value1", "", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertEquals("", record.get(1));
    }

    @Test
    public void testGet_largeIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(Integer.MAX_VALUE);
        });
    }
}
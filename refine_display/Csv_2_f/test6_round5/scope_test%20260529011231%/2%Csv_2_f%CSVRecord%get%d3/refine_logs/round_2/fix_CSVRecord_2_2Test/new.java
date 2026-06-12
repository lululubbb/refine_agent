package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_2Test {

    @Test
    public void testGet_validIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(1);
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_zeroIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(0);
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_lastIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(2);
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testGet_outOfBounds() throws Exception {
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
    public void testGet_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(0);
        });
    }

    @Test
    public void testGet_emptyArrayAndNegativeIndex() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(-1);
        });
    }

    @Test
    public void testGet_nullValue() throws Exception {
        String[] values = {null, "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(0);
        Assertions.assertEquals(null, result);
    }

    @Test
    public void testGet_emptyStringValue() throws Exception {
        String[] values = {"", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(0);
        Assertions.assertEquals("", result);
    }

    @Test
    public void testGet_largeIndex() throws Exception {
        String[] values = new String[Integer.MAX_VALUE];
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(Integer.MAX_VALUE);
        });
    }
}
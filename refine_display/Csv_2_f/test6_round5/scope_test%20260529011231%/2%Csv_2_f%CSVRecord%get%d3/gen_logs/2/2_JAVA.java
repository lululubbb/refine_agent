package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Array;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_2_2Test {

    @Test
    public void testGet_validIndex() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(1);
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_zeroIndex() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(0);
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_lastIndex() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = record.get(2);
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testGet_outOfBounds() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(3);
        });
    }

    @Test
    public void testGet_negativeIndex() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(-1);
        });
    }

    @Test
    public void testGet_emptyArray() {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(0);
        });
    }
}